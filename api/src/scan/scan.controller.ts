import {
  BadRequestException,
  Controller,
  Post,
  UploadedFile,
  UseGuards,
  UseInterceptors,
} from '@nestjs/common';
import { FileInterceptor } from '@nestjs/platform-express';
import { memoryStorage } from 'multer';
import { ApiKeyGuard } from '../common/guards/api-key.guard';
import { ScanService } from './scan.service';

@Controller('scan')
@UseGuards(ApiKeyGuard)
export class ScanController {
  constructor(private scan: ScanService) {}

  @Post('upload')
  @UseInterceptors(
    FileInterceptor('image', {
      storage: memoryStorage(),
      limits: { fileSize: 20 * 1024 * 1024 }, // 20MB
      fileFilter: (_req, file, cb) => {
        if (!['image/jpeg', 'image/jpg', 'image/png'].includes(file.mimetype)) {
          cb(new BadRequestException('Only JPEG/PNG images are accepted'), false);
          return;
        }
        cb(null, true);
      },
    }),
  )
  async upload(@UploadedFile() file: Express.Multer.File) {
    if (!file) {
      throw new BadRequestException('Image file is required');
    }
    return this.scan.initiateProcessing(file.buffer);
  }
}
