import { Injectable } from '@nestjs/common';

export interface ParsedCertificate {
  ownerName: string | null;
  parcelNumber: string | null;
  sheetNumber: string | null;
  areaM2: number | null;
  address: string | null;
  purpose: string | null;
  landUseForm: string | null;
  expiryYear: string | null;
  landOrigin: string | null;
}

@Injectable()
export class ParserService {
  parse(text: string): ParsedCertificate {
    // Normalise line endings and collapse excess whitespace per line
    const clean = text
      .replace(/\r\n/g, '\n')
      .replace(/[ \t]+/g, ' ')
      .trim();

    return {
      ownerName: this.extractOwnerName(clean),
      parcelNumber: this.extractParcelNumber(clean),
      sheetNumber: this.extractSheetNumber(clean),
      areaM2: this.extractArea(clean),
      address: this.extractAddress(clean),
      purpose: this.extractPurpose(clean),
      landUseForm: this.extractLandUseForm(clean),
      expiryYear: this.extractExpiry(clean),
      landOrigin: this.extractLandOrigin(clean),
    };
  }

  // ─── Thửa đất số ─────────────────────────────────────────────────────────

  private extractParcelNumber(text: string): string | null {
    // Format: "Thửa đất số: 123" or "thửa số: 45"
    // OCR may read "Thửa" as "Fhửa", "Thứa", etc. — match loosely
    const m = text.match(/th[uưứ][aả]\s+đ[aấ]t\s+s[oố][:\s]+([\d/]+)/i)
      ?? text.match(/th[uưứ][aả]\s+s[oố][:\s]+([\d/]+)/i)
      ?? text.match(/s[oố]\s+th[uưứ][aả][:\s]+([\d/]+)/i);
    return m?.[1]?.trim() ?? null;
  }

  // ─── Tờ bản đồ số ────────────────────────────────────────────────────────

  private extractSheetNumber(text: string): string | null {
    const m = text.match(/t[oờ]\s+b[aả]n\s+đ[oồ]\s+s[oố][:\s]+([\d/]+)/i)
      ?? text.match(/t[oờ]\s+s[oố][:\s]+([\d/]+)/i);
    return m?.[1]?.trim() ?? null;
  }

  // ─── Diện tích ───────────────────────────────────────────────────────────
  // Tesseract often reads m² as "mê", "m2", "m?", "m²"
  // There may be multiple "diện tích" lines — we need the parcel area,
  // which is always the one followed by "(bằng chữ:..." or appearing first.

  private extractArea(text: string): number | null {
    // Priority: number immediately followed by m-unit near "bằng chữ" (spelled-out amount)
    const withSpelledOut = text.match(/([\d.,]+)\s*m[ê²2?e][²2]?,?\s*\(b[aằ]ng\s+ch[uữ]/i);
    if (withSpelledOut?.[1]) {
      const n = this.parseVietnameseNumber(withSpelledOut[1]);
      if (n !== null && n > 10) return n;
    }

    // Try "diện tích: NUMBER m-unit" — take ALL matches, pick the first plausible one
    const labelPattern = /di[eệ]n\s+t[ií]ch[:\s]+([\d.,]+)\s*m/gi;
    let m: RegExpExecArray | null;
    while ((m = labelPattern.exec(text)) !== null) {
      const n = this.parseVietnameseNumber(m[1]);
      if (n !== null && n > 10 && n < 100000) return n;
    }

    // Fallback: any NUMBER followed by m-unit then "," or "(" (parcel area context)
    const fallback = text.match(/([\d.,]+)\s*m[ê²2?e][²2]?[,(]/i);
    if (fallback?.[1]) {
      const n = this.parseVietnameseNumber(fallback[1]);
      if (n !== null && n > 10 && n < 100000) return n;
    }

    return null;
  }

  // Handles both "466,5" (VN comma-decimal) and "466.5" (dot-decimal)
  private parseVietnameseNumber(raw: string): number | null {
    // Remove thousands separators (dots used as thousands sep in VN: "1.000,5")
    // Heuristic: if there's both "." and "," → "." is thousands sep, "," is decimal
    let normalized: string;
    if (raw.includes('.') && raw.includes(',')) {
      normalized = raw.replace(/\./g, '').replace(',', '.');
    } else {
      normalized = raw.replace(',', '.');
    }
    const n = parseFloat(normalized);
    return isNaN(n) ? null : n;
  }

  // ─── Địa chỉ ─────────────────────────────────────────────────────────────

  private extractAddress(text: string): string | null {
    // Label may be on same line or the value may be on the next line
    const sameLinePatterns = [
      /đ[ịi]a\s+ch[ỉi]\s+b[aấ]t\s+đ[ộo]ng\s+s[aả]n[:\s]+([^\n]{10,300})/i,
      /đ[ịi]a\s+ch[ỉi][:\s]+([^\n]{10,300})/i,
    ];
    for (const p of sameLinePatterns) {
      const m = text.match(p);
      const val = m?.[1]?.trim();
      if (val && val.length > 5) {
        return val.replace(/[,.\s]+$/, '');
      }
    }

    // Address label on its own line, value on next line
    const nextLine = text.match(/đ[ịi]a\s+ch[ỉi][:\s]*\n([^\n]{10,300})/i);
    const nextLineVal = nextLine?.[1]?.trim();
    if (nextLineVal && nextLineVal.length > 5) {
      return nextLineVal.replace(/[,.\s]+$/, '');
    }

    // Last resort: detect "Thị trấn / Phường / Xã ... Huyện / Quận ... Tp / Tỉnh"
    const cityPattern = text.match(
      /(?:th[ịi]\s+tr[aấ]n|ph[uường]+|x[aã])\s+[^\n,]{3,50},\s*[^\n,]{3,50},\s*(?:Tp|Tỉnh|TP)[^\n,]{3,80}/i,
    );
    if (cityPattern?.[0]) return cityPattern[0].trim().replace(/[,.\s]+$/, '');

    return null;
  }

  // ─── Mục đích sử dụng ────────────────────────────────────────────────────

  private extractPurpose(text: string): string | null {
    const m = text.match(/m[uụ]c\s+đ[ií]ch\s+s[uử]\s+d[uụ]ng[:\s]+([^\n]{5,150})/i)
      ?? text.match(/lo[aạ]i\s+đ[aấ]t[:\s]+([^\n]{5,100})/i);
    return m?.[1]?.trim().replace(/[,.\s]+$/, '') ?? null;
  }

  // ─── Hình thức sử dụng ───────────────────────────────────────────────────
  // OCR often drops "th" → "Hình hức", "Hình thức", "Hính thức"

  private extractLandUseForm(text: string): string | null {
    // Match "Hình" + 0-2 chars + "sử dụng" to handle OCR variants
    const m = text.match(/h[ìí]nh\s+\S{1,5}\s+s[uử]\s+d[uụ]ng[:\s]+([^\n]{3,80})/i);
    return m?.[1]?.trim().replace(/[,.\s]+$/, '') ?? null;
  }

  // ─── Thời hạn sử dụng ────────────────────────────────────────────────────

  private extractExpiry(text: string): string | null {
    const m = text.match(/th[oờ]i\s+h[aạ]n\s+s[uử]\s+d[uụ]ng[:\s]+([^\n]{4,80})/i);
    return m?.[1]?.trim().replace(/[,.\s]+$/, '') ?? null;
  }

  // ─── Nguồn gốc sử dụng ───────────────────────────────────────────────────

  private extractLandOrigin(text: string): string | null {
    const m = text.match(/ngu[oồ]n\s+g[oố]c\s+s[uử]\s+d[uụ]ng[:\s]+([^\n]{5,300})/i);
    return m?.[1]?.trim().replace(/[,.\s]+$/, '') ?? null;
  }

  // ─── Tên chủ sở hữu ──────────────────────────────────────────────────────
  // Key fix: "Ông"/"Bà" must be at start of line or after ":" — NOT inside
  // words like "không", "Công", "bằng" which contain "ông"/"bà" as substrings.

  private extractOwnerName(text: string): string | null {
    const patterns = [
      // "Người sử dụng đất: <name>"
      /ng[uư][oờ]i\s+s[uử]\s+d[uụ]ng\s+đ[aấ]t[:\s]+([^\n,]{5,100})/i,
      // "Ông/Bà: <name>"
      /[OÔ]ng\s*\/\s*[Bb][aà][:\s]+([^\n,]{5,100})/i,
      // "Ông: <name>" — only when "Ông" starts the line or comes after ":"
      /(?:^|:\s*|\n)[OÔ]ng[:\s]+([^\n,]{5,60})/m,
      // "Bà: <name>" — same rule
      /(?:^|:\s*|\n)[Bb][aà][:\s]+([^\n,]{5,60})/m,
    ];
    for (const p of patterns) {
      const m = text.match(p);
      const val = m?.[1]?.trim();
      if (val && val.length > 3) {
        return val.replace(/[,.\s]+$/, '');
      }
    }
    return null;
  }
}
