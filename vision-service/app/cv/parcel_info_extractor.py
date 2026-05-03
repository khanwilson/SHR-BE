"""
Extract land parcel fields from Section II.1 (Thửa đất) of sổ hồng.

Fields:
  thua_dat_so, to_ban_do_so, dia_chi, dien_tich,
  hinh_thuc_su_dung, muc_dich_su_dung, thoi_han_su_dung, nguon_goc_su_dung

Uses ASCII-folding (strip all Vietnamese diacritics) for robust matching
against noisy OCR output where tone marks are frequently wrong.
The fold is 1-to-1 so character positions map directly to the original text.
"""

import re

import cv2
import numpy as np
import pytesseract
from PIL import Image

from app.config import TESSERACT_LANG

# ─── Vietnamese → ASCII fold (1-to-1, position-safe) ───────────────────────

_VN_FOLD = str.maketrans({
    # a
    'à':'a','á':'a','ả':'a','ã':'a','ạ':'a',
    'ă':'a','ắ':'a','ằ':'a','ẳ':'a','ẵ':'a','ặ':'a',
    'â':'a','ấ':'a','ầ':'a','ẩ':'a','ẫ':'a','ậ':'a',
    'À':'A','Á':'A','Ả':'A','Ã':'A','Ạ':'A',
    'Ă':'A','Ắ':'A','Ằ':'A','Ẳ':'A','Ẵ':'A','Ặ':'A',
    'Â':'A','Ấ':'A','Ầ':'A','Ẩ':'A','Ẫ':'A','Ậ':'A',
    # e
    'è':'e','é':'e','ẻ':'e','ẽ':'e','ẹ':'e',
    'ê':'e','ề':'e','ế':'e','ể':'e','ễ':'e','ệ':'e',
    'È':'E','É':'E','Ẻ':'E','Ẽ':'E','Ẹ':'E',
    'Ê':'E','Ề':'E','Ế':'E','Ể':'E','Ễ':'E','Ệ':'E',
    # i
    'ì':'i','í':'i','ỉ':'i','ĩ':'i','ị':'i',
    'Ì':'I','Í':'I','Ỉ':'I','Ĩ':'I','Ị':'I',
    # o
    'ò':'o','ó':'o','ỏ':'o','õ':'o','ọ':'o',
    'ô':'o','ồ':'o','ố':'o','ổ':'o','ỗ':'o','ộ':'o',
    'ơ':'o','ờ':'o','ớ':'o','ở':'o','ỡ':'o','ợ':'o',
    'Ò':'O','Ó':'O','Ỏ':'O','Õ':'O','Ọ':'O',
    'Ô':'O','Ồ':'O','Ố':'O','Ổ':'O','Ỗ':'O','Ộ':'O',
    'Ơ':'O','Ờ':'O','Ớ':'O','Ở':'O','Ỡ':'O','Ợ':'O',
    # u
    'ù':'u','ú':'u','ủ':'u','ũ':'u','ụ':'u',
    'ư':'u','ừ':'u','ứ':'u','ử':'u','ữ':'u','ự':'u',
    'Ù':'U','Ú':'U','Ủ':'U','Ũ':'U','Ụ':'U',
    'Ư':'U','Ừ':'U','Ứ':'U','Ử':'U','Ữ':'U','Ự':'U',
    # y
    'ỳ':'y','ý':'y','ỷ':'y','ỹ':'y','ỵ':'y',
    'Ỳ':'Y','Ý':'Y','Ỷ':'Y','Ỹ':'Y','Ỵ':'Y',
    # d with stroke
    'đ':'d','Đ':'D',
})


def _fold(text: str) -> str:
    """Strip all Vietnamese diacritics (1-to-1, preserves string length)."""
    return text.translate(_VN_FOLD)


# ─── OCR helpers ────────────────────────────────────────────────────────────

def _preprocess(region: np.ndarray) -> Image.Image:
    gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    scaled = cv2.resize(gray, (w * 2, h * 2), interpolation=cv2.INTER_CUBIC)
    denoised = cv2.fastNlMeansDenoising(scaled, h=10)
    _, bw = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return Image.fromarray(bw)


def _ocr_text_section(img: np.ndarray) -> str:
    h, w = img.shape[:2]
    # Section II.1 is on the left ~58% of the page, top ~85%
    left = img[:int(h * 0.85), :int(w * 0.58)]
    pil = _preprocess(left)
    return pytesseract.image_to_string(pil, lang=TESSERACT_LANG, config="--psm 6 --oem 3")


# ─── Parser ─────────────────────────────────────────────────────────────────

def _clean(s: str) -> str:
    s = s.strip()
    s = re.sub(r'[,;:\s_\-]+$', '', s)
    return s.strip()


def _parse_fields(text: str) -> dict:
    # Flatten newlines, collapse whitespace
    flat = re.sub(r'\s*\n\s*', ' ', text)
    flat = re.sub(r'[ \t]+', ' ', flat)

    # ASCII-folded + lowercased for pattern matching (same length as flat)
    norm = _fold(flat).lower()

    # V matches any vowel — tolerates OCR tone-mark substitutions (e.g. ồ→ằ→a vs o)
    V = '[aeiou]'

    result = {}

    def _after(anchor: str, stops: list[str], max_len: int = 400) -> str | None:
        """
        Find `anchor` in norm, return the slice of `flat` that follows up to
        the first stop match (or max_len chars).
        Positions are valid because _fold() is strictly 1-to-1.
        """
        m = re.search(anchor, norm, re.IGNORECASE)
        if not m:
            return None
        start = m.end()
        end = start + max_len
        for sp in stops:
            sm = re.search(sp, norm[start : start + max_len], re.IGNORECASE)
            if sm:
                end = min(end, start + sm.start())
        val = flat[start:end]
        # Strip trailing OCR label artifacts like " ©)", " £)", " 4)", " b)"
        val = re.sub(r'\s+[©£\da-g]\s*\)\s*$', '', val, flags=re.IGNORECASE)
        val = re.sub(r'\s+\)\s*$', '', val)  # lone ")" leftover
        return _clean(val) or None

    # a) Thửa đất số NNN
    m = re.search(rf'thu{V}\s*d{V}t\s*s{V}\s*[;:\-]?\s*([#\d]+)', norm)
    if m:
        val = re.sub(r'[^\d#]', '', m.group(1)).replace('#', '8')
        if val:
            result['thua_dat_so'] = val

    # same line: tờ bản đồ số NNN
    m = re.search(rf'b{V}n\s*d{V}\s*s{V}\s*[;:\-]?\s*(\d+)', norm)
    if m:
        pos = m.start(1)
        result['to_ban_do_so'] = flat[pos : pos + len(m.group(1))]

    # b) Địa chỉ
    val = _after(
        rf'd{V}{V}\s*ch{V}\s*[;:\s]+',
        [rf'd{V}{V}n\s*t{V}ch', r'[c©]\s*\)'],
    )
    if val:
        result['dia_chi'] = val

    # c) Diện tích: NNN,Nm²
    m = re.search(rf'd{V}{V}n\s*t{V}ch\s*[;:\s(]+([0-9][0-9,.]*\s*m[²³2]?)', norm)
    if m:
        pos = m.start(1)
        result['dien_tich'] = flat[pos : pos + len(m.group(1))].strip()

    # d) Hình thức sử dụng
    val = _after(
        rf'h{V}nh\s*th{V}c\s*s{V}\s*d{V}ng\s*[;:\s]+',
        [rf'm{V}c\s*d{V}ch', r'[de©4]\s*\)'],
    )
    if val:
        result['hinh_thuc_su_dung'] = val

    # đ) Mục đích sử dụng
    val = _after(
        rf'm{V}c\s*d{V}ch\s*s{V}\s*d{V}ng\s*[;:\s]+',
        [rf'th{V}{V}\s*h{V}n', r'[e©]\s*\)'],
    )
    if val:
        result['muc_dich_su_dung'] = val

    # e) Thời hạn sử dụng
    # Stop on any "ngu<vowel>" — handles "nguồn"→"nguon", "nguằn"→"nguan", etc.
    val = _after(
        rf'th{V}{V}\s*h{V}n\s*s{V}\s*d{V}ng\s*[;:\s]+',
        [rf'ngu{V}', r'[g£]\s*\)'],
    )
    if val:
        result['thoi_han_su_dung'] = val

    # g) Nguồn gốc sử dụng
    # "nguồn" can OCR to any vowel; "gốc" often truncated to "gc"
    val = _after(
        rf'ngu{V}n?\s*g{V}?c?\s*s{V}\s*d{V}ng\s*[;:\s]+',
        # "\d. " catches next numbered section like "2. Nhà ở" even when OCR mangled the label
        [r'\s+\d\.\s+', r'\d+\.\s*nha', r'\d+\.\s*cong\s*trinh', r'ghi\s*chu'],
    )
    if val:
        result['nguon_goc_su_dung'] = val

    return result


# ─── Public API ─────────────────────────────────────────────────────────────

def extract_parcel_info(img: np.ndarray) -> dict:
    """Extract Section II.1 land parcel fields from the full document image."""
    try:
        text = _ocr_text_section(img)
        fields = _parse_fields(text)
        return {"success": bool(fields), "fields": fields}
    except Exception as exc:  # noqa: BLE001
        return {"success": False, "fields": {}, "error": str(exc)}


def parse_parcel_info_from_text(raw_ocr_text: str) -> dict:
    """
    Parse parcel fields directly from already-extracted OCR text.
    Use this when OCR is done externally (e.g. Google Vision, Claude Vision).
    """
    fields = _parse_fields(raw_ocr_text)
    return {"success": bool(fields), "fields": fields}
