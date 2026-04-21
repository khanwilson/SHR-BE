import { BullModule } from '@nestjs/bullmq';
import { Module } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { CertificatesModule } from '../certificates/certificates.module';
import { JobsModule } from '../jobs/jobs.module';
import { OcrModule } from '../ocr/ocr.module';
import { ParserModule } from '../parser/parser.module';
import { StorageModule } from '../storage/storage.module';
import { VisionModule } from '../vision/vision.module';
import { ScanProcessor } from './processors/scan.processor';
import { ScanProducer } from './producers/scan.producer';
import { SCAN_QUEUE } from './queue.constants';

@Module({
  imports: [
    BullModule.registerQueueAsync({
      name: SCAN_QUEUE,
      inject: [ConfigService],
      useFactory: (config: ConfigService) => ({
        connection: {
          url: config.get<string>('redis.url'),
        },
        defaultJobOptions: {
          attempts: 2,
          backoff: { type: 'exponential', delay: 30000 },
          removeOnComplete: { count: 100 },
          removeOnFail: { count: 50 },
        },
      }),
    }),
    JobsModule,
    CertificatesModule,
    OcrModule,
    ParserModule,
    VisionModule,
    StorageModule,
  ],
  providers: [ScanProcessor, ScanProducer],
  exports: [ScanProducer],
})
export class QueueModule {}
