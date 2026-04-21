import { Module } from '@nestjs/common';
import { HttpModule } from '@nestjs/axios';
import { OcrService } from './ocr.service';
import { GoogleVisionProvider } from './providers/google-vision.provider';
import { TesseractProvider } from './providers/tesseract.provider';

@Module({
  imports: [HttpModule],
  providers: [OcrService, GoogleVisionProvider, TesseractProvider],
  exports: [OcrService],
})
export class OcrModule {}
