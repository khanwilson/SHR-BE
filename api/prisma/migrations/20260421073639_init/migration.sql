-- CreateEnum
CREATE TYPE "JobStatus" AS ENUM ('QUEUED', 'PROCESSING', 'COMPLETED', 'FAILED');

-- CreateTable
CREATE TABLE "certificates" (
    "id" TEXT NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,
    "deletedAt" TIMESTAMP(3),
    "ownerName" TEXT,
    "parcelNumber" TEXT,
    "sheetNumber" TEXT,
    "areaM2" DOUBLE PRECISION,
    "address" TEXT,
    "purpose" TEXT,
    "expiryDate" TIMESTAMP(3),
    "ocrRawText" TEXT,
    "ocrProvider" TEXT NOT NULL DEFAULT 'google_vision',
    "ocrConfidence" DOUBLE PRECISION,
    "originalImagePath" TEXT,

    CONSTRAINT "certificates_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "parcel_diagrams" (
    "id" TEXT NOT NULL,
    "certificateId" TEXT NOT NULL,
    "vertices" JSONB NOT NULL,
    "edges" JSONB NOT NULL,
    "confidence" DOUBLE PRECISION NOT NULL,
    "vertexCount" INTEGER NOT NULL,
    "extractionError" TEXT,
    "diagramImagePath" TEXT,

    CONSTRAINT "parcel_diagrams_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "jobs" (
    "id" TEXT NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,
    "status" "JobStatus" NOT NULL DEFAULT 'QUEUED',
    "progress" INTEGER NOT NULL DEFAULT 0,
    "error" TEXT,
    "uploadedImagePath" TEXT,
    "certificateId" TEXT,

    CONSTRAINT "jobs_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE INDEX "certificates_ownerName_idx" ON "certificates"("ownerName");

-- CreateIndex
CREATE INDEX "certificates_parcelNumber_idx" ON "certificates"("parcelNumber");

-- CreateIndex
CREATE INDEX "certificates_createdAt_idx" ON "certificates"("createdAt");

-- CreateIndex
CREATE UNIQUE INDEX "parcel_diagrams_certificateId_key" ON "parcel_diagrams"("certificateId");

-- CreateIndex
CREATE UNIQUE INDEX "jobs_certificateId_key" ON "jobs"("certificateId");

-- CreateIndex
CREATE INDEX "jobs_status_idx" ON "jobs"("status");

-- CreateIndex
CREATE INDEX "jobs_createdAt_idx" ON "jobs"("createdAt");

-- AddForeignKey
ALTER TABLE "parcel_diagrams" ADD CONSTRAINT "parcel_diagrams_certificateId_fkey" FOREIGN KEY ("certificateId") REFERENCES "certificates"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "jobs" ADD CONSTRAINT "jobs_certificateId_fkey" FOREIGN KEY ("certificateId") REFERENCES "certificates"("id") ON DELETE SET NULL ON UPDATE CASCADE;
