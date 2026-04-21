import { Injectable, Logger } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import * as fs from 'fs/promises';
import { GoogleVisionProvider } from './providers/google-vision.provider';
import { TesseractProvider } from './providers/tesseract.provider';

@Injectable()
export class OcrService {
  private readonly logger = new Logger(OcrService.name);

  constructor(
    private config: ConfigService,
    private googleVision: GoogleVisionProvider,
    private tesseract: TesseractProvider,
  ) {}

  async extract(imagePath: string): Promise<{ text: string; provider: string }> {
    const buffer = await fs.readFile(imagePath);
    const provider = this.config.get<string>('ocr.provider');
    const hasCredentials = !!this.config.get<string>('ocr.googleCredentials');

    if (provider === 'google_vision' && hasCredentials) {
      try {
        const text = await this.googleVision.extract(buffer);
        return { text, provider: 'google_vision' };
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : String(err);
        this.logger.warn(`Google Vision failed, falling back to Tesseract: ${message}`);
      }
    }

    const text = await this.tesseract.extract(buffer);
    return { text, provider: 'tesseract' };
  }
}
