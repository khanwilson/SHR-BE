-- AlterTable
ALTER TABLE "parcel_diagrams" ADD COLUMN     "coordinatesVn2000" JSONB,
ADD COLUMN     "extractionSource" TEXT NOT NULL DEFAULT 'polygon_detection';
