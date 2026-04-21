import { Injectable } from '@nestjs/common';
import { randomUUID } from 'crypto';
import { JobsService } from '../jobs/jobs.service';
import { StorageService } from '../storage/storage.service';
import { ScanProducer } from '../queue/producers/scan.producer';

@Injectable()
export class ScanService {
  constructor(
    private jobs: JobsService,
    private storage: StorageService,
    private producer: ScanProducer,
  ) {}

  async initiateProcessing(imageBuffer: Buffer) {
    const uploadId = randomUUID();

    // Save uploaded image
    const { filePath } = await this.storage.saveUpload(imageBuffer, uploadId, 'original.jpg');

    // Create job record
    const job = await this.jobs.create(filePath);

    // Enqueue processing
    await this.producer.enqueue({ jobId: job.id, imagePath: filePath });

    return {
      jobId: job.id,
      status: 'queued',
      estimatedSeconds: 8,
    };
  }
}
