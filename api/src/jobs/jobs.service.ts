import { Injectable, NotFoundException } from '@nestjs/common';
import { JobStatus } from '@prisma/client';
import { PrismaService } from '../prisma/prisma.service';

@Injectable()
export class JobsService {
  constructor(private prisma: PrismaService) {}

  async create(uploadedImagePath: string) {
    return this.prisma.job.create({ data: { uploadedImagePath } });
  }

  async findById(id: string) {
    const job = await this.prisma.job.findUnique({
      where: { id },
      include: {
        certificate: {
          include: { parcelDiagram: true },
        },
      },
    });
    if (!job) throw new NotFoundException(`Job ${id} not found`);
    return job;
  }

  async markProcessing(id: string) {
    return this.prisma.job.update({
      where: { id },
      data: { status: JobStatus.PROCESSING, progress: 10 },
    });
  }

  async updateProgress(id: string, progress: number) {
    return this.prisma.job.update({ where: { id }, data: { progress } });
  }

  async markCompleted(id: string, certificateId: string) {
    return this.prisma.job.update({
      where: { id },
      data: { status: JobStatus.COMPLETED, progress: 100, certificateId },
    });
  }

  async markFailed(id: string, error: string) {
    return this.prisma.job.update({
      where: { id },
      data: { status: JobStatus.FAILED, error },
    });
  }

  async resetStalledJobs() {
    await this.prisma.job.updateMany({
      where: { status: JobStatus.PROCESSING },
      data: { status: JobStatus.FAILED, error: 'Process restarted' },
    });
  }
}
