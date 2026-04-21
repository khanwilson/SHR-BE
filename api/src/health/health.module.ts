import { Module } from '@nestjs/common';
import { VisionModule } from '../vision/vision.module';
import { HealthController } from './health.controller';

@Module({
  imports: [VisionModule],
  controllers: [HealthController],
})
export class HealthModule {}
