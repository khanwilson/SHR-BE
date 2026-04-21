import { InjectQueue } from '@nestjs/bullmq';
import { Injectable } from '@nestjs/common';
import { Queue } from 'bullmq';
import { SCAN_QUEUE } from '../queue.constants';

export interface ScanJobData {
  jobId: string;
  imagePath: string;
}

@Injectable()
export class ScanProducer {
  constructor(@InjectQueue(SCAN_QUEUE) private queue: Queue) {}

  async enqueue(data: ScanJobData) {
    return this.queue.add('extract', data, { jobId: data.jobId });
  }
}
