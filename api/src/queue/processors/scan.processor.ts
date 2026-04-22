import { Processor, WorkerHost } from '@nestjs/bullmq';
import { Logger } from '@nestjs/common';
import { Job } from 'bullmq';
import { CertificatesService } from '../../certificates/certificates.service';
import { JobsService } from '../../jobs/jobs.service';
import { OcrService } from '../../ocr/ocr.service';
import { ParserService } from '../../parser/parser.service';
import { StorageService } from '../../storage/storage.service';
import { VisionService } from '../../vision/vision.service';
import { SCAN_QUEUE } from '../queue.constants';
import { ScanJobData } from '../producers/scan.producer';

@Processor(SCAN_QUEUE)
export class ScanProcessor extends WorkerHost {
  private readonly logger = new Logger(ScanProcessor.name);

  constructor(
    private jobs: JobsService,
    private ocr: OcrService,
    private parser: ParserService,
    private vision: VisionService,
    private certificates: CertificatesService,
    private storage: StorageService,
  ) {
    super();
  }

  async process(job: Job<ScanJobData>) {
    const { jobId, imagePath } = job.data;
    this.logger.log(`Processing job ${jobId}`);

    try {
      await this.jobs.markProcessing(jobId);

      // Step 1: OCR (Google Vision → Tesseract fallback)
      await this.jobs.updateProgress(jobId, 20);
      const { text, provider } = await this.ocr.extract(imagePath);
      this.logger.log(`OCR done (${provider}): ${text.length} chars`);

      // Step 2: Parse Vietnamese fields
      await this.jobs.updateProgress(jobId, 40);
      const fields = this.parser.parse(text);

      // Step 3: OpenCV parcel diagram — non-fatal, vision-service may not be running
      await this.jobs.updateProgress(jobId, 60);
      const diagram = await this.vision.extractParcelDiagram(imagePath);

      // Step 4: Persist certificate
      await this.jobs.updateProgress(jobId, 80);
      const certificate = await this.certificates.create({
        ...fields,
        ocrRawText: text,
        ocrProvider: provider,
        originalImagePath: imagePath,
      });

      // Step 5: Save parcel diagram if extracted successfully
      if (diagram.success && diagram.vertices.length >= 3) {
        let diagramImagePath: string | undefined;
        if (diagram.diagramImageBase64) {
          const imgBuffer = Buffer.from(diagram.diagramImageBase64, 'base64');
          const saved = await this.storage.saveDiagramImage(imgBuffer, certificate.id);
          diagramImagePath = saved.filePath;
        }
        await this.certificates.createParcelDiagram(certificate.id, diagram, diagramImagePath);
      }

      await this.jobs.markCompleted(jobId, certificate.id);
      this.logger.log(`Job ${jobId} completed → certificate ${certificate.id}`);

    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err);
      this.logger.error(`Job ${jobId} failed: ${message}`);
      await this.jobs.markFailed(jobId, message).catch(() => null);
      throw err; // re-throw so BullMQ records the failure
    }
  }
}
