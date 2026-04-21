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

    await this.jobs.markProcessing(jobId);

    // Step 1: OCR
    await this.jobs.updateProgress(jobId, 20);
    const { text, provider } = await this.ocr.extract(imagePath);

    // Step 2: Parse Vietnamese fields
    await this.jobs.updateProgress(jobId, 40);
    const fields = this.parser.parse(text);

    // Step 3: OpenCV parcel diagram
    await this.jobs.updateProgress(jobId, 60);
    const diagram = await this.vision.extractParcelDiagram(imagePath);

    // Step 4: Save diagram image if available
    let diagramImagePath: string | undefined;
    if (diagram.diagramImageBase64) {
      const imgBuffer = Buffer.from(diagram.diagramImageBase64, 'base64');
      // Derive certificateId from jobId for now — will be replaced after create
      const tempId = jobId;
      const saved = await this.storage.saveDiagramImage(imgBuffer, tempId);
      diagramImagePath = saved.filePath;
    }

    // Step 5: Persist certificate
    await this.jobs.updateProgress(jobId, 80);
    const certificate = await this.certificates.create({
      ...fields,
      ocrRawText: text,
      ocrProvider: provider,
      originalImagePath: imagePath,
    });

    // Save diagram with correct certificateId
    if (diagram.success && diagram.vertices.length >= 3) {
      let finalDiagramPath = diagramImagePath;
      if (diagram.diagramImageBase64) {
        const imgBuffer = Buffer.from(diagram.diagramImageBase64, 'base64');
        const saved = await this.storage.saveDiagramImage(imgBuffer, certificate.id);
        finalDiagramPath = saved.filePath;
      }
      await this.certificates.createParcelDiagram(certificate.id, diagram, finalDiagramPath);
    }

    // Step 6: Complete
    await this.jobs.markCompleted(jobId, certificate.id);
    this.logger.log(`Job ${jobId} completed → certificate ${certificate.id}`);
  }
}
