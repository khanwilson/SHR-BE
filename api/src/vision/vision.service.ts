import { Injectable, Logger } from '@nestjs/common';
import { HttpService } from '@nestjs/axios';
import { ConfigService } from '@nestjs/config';
import { firstValueFrom } from 'rxjs';
// eslint-disable-next-line @typescript-eslint/no-require-imports
const FormData = require('form-data') as typeof import('form-data');

export interface ParcelVertex {
  x: number;
  y: number;
}

export interface ParcelEdge {
  from: number;
  to: number;
  length_m: number | null;
  confidence: number;
  raw_text?: string;
}

export interface ParcelDiagramResult {
  success: boolean;
  vertices: ParcelVertex[];
  edges: ParcelEdge[];
  confidence: number;
  vertexCount: number;
  diagramImageBase64?: string;
  error?: string;
  source?: 'coordinate_table' | 'polygon_detection';
  coordinatesVn2000?: Array<{ point: number; northing: number; easting: number; edge_m: number | null }>;
}

@Injectable()
export class VisionService {
  private readonly logger = new Logger(VisionService.name);

  constructor(
    private http: HttpService,
    private config: ConfigService,
  ) {}

  async extractParcelDiagram(imagePath: string): Promise<ParcelDiagramResult> {
    const { readFile } = await import('fs/promises');
    const buffer = await readFile(imagePath);
    return this.extractParcelDiagramFromBuffer(buffer);
  }

  async extractParcelDiagramFromBuffer(buffer: Buffer): Promise<ParcelDiagramResult> {
    const visionUrl = this.config.get<string>('visionService.url');
    const form = new FormData();
    form.append('image', buffer, { filename: 'image.jpg', contentType: 'image/jpeg' });

    try {
      const response = await this.withRetry(  // 1 attempt in dev until vision-service is up
        () => firstValueFrom(
          this.http.post<Record<string, unknown>>(`${visionUrl}/parcel/extract`, form, {
            headers: form.getHeaders(),
            timeout: 15000,
          }),
        ),
        1,
      );
      // Python returns snake_case — map to camelCase interface
      const raw = response.data;
      const result: ParcelDiagramResult = {
        success: raw['success'] as boolean,
        vertices: (raw['vertices'] as ParcelVertex[]) ?? [],
        edges: (raw['edges'] as ParcelEdge[]) ?? [],
        confidence: (raw['confidence'] as number) ?? 0,
        vertexCount: (raw['vertex_count'] as number) ?? (raw['vertexCount'] as number) ?? 0,
        diagramImageBase64: (raw['diagram_image_b64'] as string) ?? undefined,
        source: raw['source'] as 'coordinate_table' | 'polygon_detection' | undefined,
        coordinatesVn2000: raw['coordinates_vn2000'] as ParcelDiagramResult['coordinatesVn2000'],
        error: raw['error'] as string | undefined,
      };
      this.logger.log(`Parcel extraction (${result.source ?? 'unknown'}): ${result.vertexCount} vertices, confidence ${result.confidence}`);
      return result;
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err);
      this.logger.error(`Vision service failed: ${message}`);
      return { success: false, vertices: [], edges: [], confidence: 0, vertexCount: 0, error: message };
    }
  }

  async healthCheck(): Promise<boolean> {
    const visionUrl = this.config.get<string>('visionService.url');
    try {
      await firstValueFrom(this.http.get(`${visionUrl}/health`, { timeout: 5000 }));
      return true;
    } catch {
      return false;
    }
  }

  private async withRetry<T>(fn: () => Promise<T>, attempts: number): Promise<T> {
    for (let i = 0; i < attempts; i++) {
      try {
        return await fn();
      } catch (err) {
        if (i === attempts - 1) throw err;
        const delay = Math.pow(2, i) * 1000;
        await new Promise((r) => setTimeout(r, delay));
        this.logger.warn(`Vision service retry ${i + 1}/${attempts}`);
      }
    }
    throw new Error('Unreachable');
  }
}
