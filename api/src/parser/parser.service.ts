import { Injectable } from '@nestjs/common';

interface FieldResult {
  value: string | number | null;
  confidence: number;
}

interface ParsedCertificate {
  ownerName: string | null;
  parcelNumber: string | null;
  sheetNumber: string | null;
  areaM2: number | null;
  address: string | null;
  purpose: string | null;
}

@Injectable()
export class ParserService {
  parse(text: string): ParsedCertificate {
    return {
      ownerName: this.extractOwnerName(text).value as string | null,
      parcelNumber: this.extractParcelNumber(text).value as string | null,
      sheetNumber: this.extractSheetNumber(text).value as string | null,
      areaM2: this.extractArea(text).value as number | null,
      address: this.extractAddress(text).value as string | null,
      purpose: this.extractPurpose(text).value as string | null,
    };
  }

  private extractParcelNumber(text: string): FieldResult {
    const patterns = [
      /thửa\s+đất\s+số[:\s]+(\d+)/i,
      /thửa\s+số[:\s]+(\d+)/i,
      /số\s+thửa[:\s]+(\d+)/i,
      /thửa[:\s]+(\d+)/i,
    ];
    return this.firstMatch(text, patterns);
  }

  private extractSheetNumber(text: string): FieldResult {
    const patterns = [
      /tờ\s+bản\s+đồ\s+số[:\s]+(\d+)/i,
      /tờ\s+số[:\s]+(\d+)/i,
      /bản\s+đồ\s+số[:\s]+(\d+)/i,
    ];
    return this.firstMatch(text, patterns);
  }

  private extractArea(text: string): FieldResult {
    const patterns = [
      /diện\s+tích[:\s]+([\d.,]+)\s*m[²2]/i,
      /diện\s+tích[:\s]+([\d.,]+)/i,
    ];
    const result = this.firstMatch(text, patterns);
    if (result.value) {
      const normalized = (result.value as string).replace(',', '.');
      return { value: parseFloat(normalized), confidence: result.confidence };
    }
    return result;
  }

  private extractOwnerName(text: string): FieldResult {
    const patterns = [
      /người\s+sử\s+dụng\s+đất[:\s]+([^\n,]{5,80})/i,
      /ông\s*\/?\s*bà[:\s]+([^\n,]{5,80})/i,
      /ông[:\s]+([^\n,]{5,60})/i,
      /bà[:\s]+([^\n,]{5,60})/i,
    ];
    const result = this.firstMatch(text, patterns);
    if (result.value) {
      return { value: (result.value as string).trim(), confidence: result.confidence };
    }
    return result;
  }

  private extractAddress(text: string): FieldResult {
    const patterns = [
      /địa\s+chỉ[:\s]+([^\n]{10,200})/i,
      /tại[:\s]+([^\n]{10,200})/i,
      /(?:xã|phường|thị\s+trấn)[:\s]+([^\n]{5,200})/i,
    ];
    return this.firstMatch(text, patterns);
  }

  private extractPurpose(text: string): FieldResult {
    const patterns = [
      /mục\s+đích\s+sử\s+dụng[:\s]+([^\n]{5,100})/i,
      /loại\s+đất[:\s]+([^\n]{5,50})/i,
    ];
    return this.firstMatch(text, patterns);
  }

  private firstMatch(text: string, patterns: RegExp[]): FieldResult {
    for (const pattern of patterns) {
      const match = text.match(pattern);
      if (match?.[1]) {
        return { value: match[1].trim(), confidence: 0.8 };
      }
    }
    return { value: null, confidence: 0 };
  }
}
