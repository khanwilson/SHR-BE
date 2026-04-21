import { Module } from '@nestjs/common';
import { JobsModule } from '../jobs/jobs.module';
import { QueueModule } from '../queue/queue.module';
import { StorageModule } from '../storage/storage.module';
import { ScanController } from './scan.controller';
import { ScanService } from './scan.service';

@Module({
  imports: [JobsModule, StorageModule, QueueModule],
  controllers: [ScanController],
  providers: [ScanService],
})
export class ScanModule {}
