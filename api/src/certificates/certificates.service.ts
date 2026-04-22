import { Injectable, NotFoundException } from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service';
import { ParcelDiagramResult } from '../vision/vision.service';

export interface CreateCertificateInput {
  ownerName?: string | null;
  parcelNumber?: string | null;
  sheetNumber?: string | null;
  areaM2?: number | null;
  address?: string | null;
  purpose?: string | null;
  landUseForm?: string | null;
  expiryYear?: string | null;
  landOrigin?: string | null;
  ocrRawText?: string | null;
  ocrProvider?: string;
  originalImagePath?: string;
}

export interface UpdateCertificateInput {
  ownerName?: string;
  parcelNumber?: string;
  sheetNumber?: string;
  areaM2?: number;
  address?: string;
  purpose?: string;
  landUseForm?: string;
  expiryYear?: string;
  landOrigin?: string;
}

@Injectable()
export class CertificatesService {
  constructor(private prisma: PrismaService) {}

  async create(input: CreateCertificateInput) {
    return this.prisma.certificate.create({ data: input });
  }

  async createParcelDiagram(certificateId: string, diagram: ParcelDiagramResult, diagramImagePath?: string) {
    return this.prisma.parcelDiagram.create({
      data: {
        certificateId,
        vertices: diagram.vertices as object[],
        edges: diagram.edges as object[],
        confidence: diagram.confidence,
        vertexCount: diagram.vertexCount ?? diagram.vertices.length,
        diagramImagePath,
        extractionSource: diagram.source ?? 'polygon_detection',
        coordinatesVn2000: diagram.coordinatesVn2000 ? (diagram.coordinatesVn2000 as object[]) : undefined,
      },
    });
  }

  async findAll(page: number, limit: number, search?: string) {
    const where = search
      ? {
          deletedAt: null,
          OR: [
            { ownerName: { contains: search, mode: 'insensitive' as const } },
            { parcelNumber: { contains: search, mode: 'insensitive' as const } },
            { address: { contains: search, mode: 'insensitive' as const } },
          ],
        }
      : { deletedAt: null };

    const [items, total] = await Promise.all([
      this.prisma.certificate.findMany({
        where,
        include: { parcelDiagram: true },
        orderBy: { createdAt: 'desc' },
        skip: (page - 1) * limit,
        take: limit,
      }),
      this.prisma.certificate.count({ where }),
    ]);

    return { items, total, page, limit };
  }

  async findById(id: string) {
    const cert = await this.prisma.certificate.findFirst({
      where: { id, deletedAt: null },
      include: { parcelDiagram: true },
    });
    if (!cert) throw new NotFoundException(`Certificate ${id} not found`);
    return cert;
  }

  async update(id: string, input: UpdateCertificateInput) {
    await this.findById(id);
    return this.prisma.certificate.update({
      where: { id },
      data: { ...input },
      include: { parcelDiagram: true },
    });
  }

  async softDelete(id: string) {
    await this.findById(id);
    return this.prisma.certificate.update({
      where: { id },
      data: { deletedAt: new Date() },
    });
  }
}
