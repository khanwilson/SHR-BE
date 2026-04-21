import { Controller, Get } from '@nestjs/common';
import { VisionService } from '../vision/vision.service';

@Controller('health')
export class HealthController {
  constructor(private vision: VisionService) {}

  @Get()
  health() {
    return { status: 'ok', service: 'shr-api' };
  }

  @Get('vision')
  async visionHealth() {
    const ok = await this.vision.healthCheck();
    return { status: ok ? 'ok' : 'unreachable', service: 'shr-vision' };
  }
}
