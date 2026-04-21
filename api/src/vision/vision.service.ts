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
      const response = await this.withRetry(
        () => firstValueFrom(
          this.http.post<ParcelDiagramResult>(`${visionUrl}/parcel/extract`, form, {
            headers: form.getHeaders(),
            timeout: 60000,
          }),
        ),
        3,
      );
      this.logger.log(`Parcel extraction: ${response.data.vertexCount} vertices, confidence ${response.data.confidence}`);
      return response.data;
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
