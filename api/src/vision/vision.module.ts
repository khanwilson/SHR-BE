import { Module } from '@nestjs/common';
import { HttpModule } from '@nestjs/axios';
import { VisionService } from './vision.service';

@Module({
  imports: [HttpModule],
  providers: [VisionService],
  exports: [VisionService],
})
export class VisionModule {}
