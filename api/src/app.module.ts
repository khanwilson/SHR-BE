import { BullModule } from '@nestjs/bullmq';
import { Module } from '@nestjs/common';
import { ConfigModule, ConfigService } from '@nestjs/config';
import { ServeStaticModule } from '@nestjs/serve-static';
import { CertificatesModule } from './certificates/certificates.module';
import { configuration } from './common/config/configuration';
import { JobsModule } from './jobs/jobs.module';
import { OcrModule } from './ocr/ocr.module';
import { ParserModule } from './parser/parser.module';
import { PrismaModule } from './prisma/prisma.module';
import { QueueModule } from './queue/queue.module';
import { ScanModule } from './scan/scan.module';
import { StorageModule } from './storage/storage.module';
import { VisionModule } from './vision/vision.module';
import { HealthModule } from './health/health.module';

@Module({
  imports: [
    ConfigModule.forRoot({ isGlobal: true, load: [configuration] }),
    BullModule.forRootAsync({
      inject: [ConfigService],
      useFactory: (config: ConfigService) => ({
        connection: { url: config.get<string>('redis.url') },
      }),
    }),
    ServeStaticModule.forRootAsync({
      inject: [ConfigService],
      useFactory: (config: ConfigService) => [
        {
          rootPath: config.get<string>('storage.path') ?? './storage',
          serveRoot: '/storage',
        },
      ],
    }),
    PrismaModule,
    StorageModule,
    JobsModule,
    OcrModule,
    ParserModule,
    VisionModule,
    CertificatesModule,
    QueueModule,
    ScanModule,
    HealthModule,
  ],
})
export class AppModule {}
