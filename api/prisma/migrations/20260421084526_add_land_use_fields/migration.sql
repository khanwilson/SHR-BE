/*
  Warnings:

  - You are about to drop the column `expiryDate` on the `certificates` table. All the data in the column will be lost.

*/
-- AlterTable
ALTER TABLE "certificates" DROP COLUMN "expiryDate",
ADD COLUMN     "expiryYear" TEXT,
ADD COLUMN     "landOrigin" TEXT,
ADD COLUMN     "landUseForm" TEXT;
