import { Injectable, Logger } from '@nestjs/common';
import { ImageAnnotatorClient } from '@google-cloud/vision';

@Injectable()
export class GoogleVisionProvider {
  private readonly logger = new Logger(GoogleVisionProvider.name);
  private client: ImageAnnotatorClient | null = null;

  private getClient(): ImageAnnotatorClient {
    if (!this.client) {
      this.client = new ImageAnnotatorClient();
    }
    return this.client;
  }

  async extract(buffer: Buffer): Promise<string> {
    const client = this.getClient();
    const [result] = await client.documentTextDetection({ image: { content: buffer } });
    const fullText = result.fullTextAnnotation?.text ?? '';
    this.logger.debug(`Google Vision extracted ${fullText.length} chars`);
    return fullText;
  }
}
