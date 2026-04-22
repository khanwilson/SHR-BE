import { Injectable, Logger } from '@nestjs/common';
import { HttpService } from '@nestjs/axios';
import { ConfigService } from '@nestjs/config';
import { firstValueFrom } from 'rxjs';
// eslint-disable-next-line @typescript-eslint/no-require-imports
const FormData = require('form-data') as typeof import('form-data');

@Injectable()
export class TesseractProvider {
  private readonly logger = new Logger(TesseractProvider.name);

  constructor(
    private http: HttpService,
    private config: ConfigService,
  ) {}

  async extract(buffer: Buffer): Promise<string> {
    const visionUrl = this.config.get<string>('visionService.url');
    const form = new FormData();
    form.append('image', buffer, { filename: 'image.jpg', contentType: 'image/jpeg' });

    try {
      const response = await firstValueFrom(
        this.http.post<{ text: string }>(`${visionUrl}/ocr/extract`, form, {
          headers: form.getHeaders(),
          timeout: 10000,
        }),
      );
      this.logger.debug(`Tesseract extracted ${response.data.text.length} chars`);
      return response.data.text;
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err);
      this.logger.warn(`Tesseract OCR unavailable (${message}), returning empty text`);
      return '';
    }
  }
}
