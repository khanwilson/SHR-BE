import { Controller, Get, Param, UseGuards } from '@nestjs/common';
import { ApiKeyGuard } from '../common/guards/api-key.guard';
import { JobsService } from './jobs.service';

@Controller('jobs')
@UseGuards(ApiKeyGuard)
export class JobsController {
  constructor(private jobs: JobsService) {}

  @Get(':id')
  async findOne(@Param('id') id: string) {
    const job = await this.jobs.findById(id);
    return {
      jobId: job.id,
      status: job.status,
      progress: job.progress,
      error: job.error ?? undefined,
      certificateId: job.certificateId ?? undefined,
      result: job.status === 'COMPLETED' && job.certificate
        ? {
            certificate: job.certificate,
            parcelDiagram: job.certificate.parcelDiagram ?? null,
          }
        : undefined,
    };
  }
}
