"""
Extract parcel polygon from the coordinate table (BẢNG LIỆT KÊ TỌA ĐỘ GÓC RANH).

Modern sổ hồng (Nghị định 43/2014) contains a table with columns:
  Số hiệu điểm | X(m) | Y(m) | Cạnh

X = northing (VN2000), Y = easting (VN2000), Cạnh = edge length in metres.
Uses bounding-box column detection so OCR character noise doesn't break row parsing.
"""

import re

import cv2
import numpy as np
import pytesseract
from PIL import Image

from app.config import TESSERACT_LANG

# Patterns to extract numbers from noisy OCR text
_NUM_RE = re.compile(r"[1lIoO]?[\d.,lIoO]{3,}")  # raw token → clean to number

# VN2000 southward zone expected ranges
_NORTHING_MIN, _NORTHING_MAX = 1_100_000, 1_400_000
_NORTHING_TRUNC_MIN, _NORTHING_TRUNC_MAX = 110_000, 140_000  # OCR drops last digit
_EASTING_MIN, _EASTING_MAX = 400_000, 800_000
_EDGE_MIN, _EDGE_MAX = 0.5, 500.0


def _fix_ocr_digits(s: str) -> str:
    """Fix common digit-letter substitutions in Tesseract output."""
    return (s.replace("l", "1").replace("I", "1").replace("O", "0")
              .replace("o", "0").replace(",", "."))


def _to_float(s: str) -> float | None:
    try:
        cleaned = _fix_ocr_digits(re.sub(r"[^0-9.,lIoO]", "", s))
        # Normalise: if both '.' and ',' present, '.' = thousands sep in VN
        if "." in cleaned and "," in cleaned:
            cleaned = cleaned.replace(".", "").replace(",", ".")
        cleaned = cleaned.replace(",", ".")
        return float(cleaned)
    except (ValueError, TypeError):
        return None


def _preprocess_for_ocr(region: np.ndarray) -> Image.Image:
    gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
    # Upscale 3x so small table digits are readable (target ~90–120px per char)
    h, w = gray.shape
    scaled = cv2.resize(gray, (w * 3, h * 3), interpolation=cv2.INTER_CUBIC)
    # Mild denoise then Otsu binarise
    denoised = cv2.fastNlMeansDenoising(scaled, h=8)
    _, bw = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return Image.fromarray(bw)


def _locate_table_region(img: np.ndarray) -> np.ndarray:
    """
    Find the coordinate table using horizontal-line density.
    Falls back to lower-right quadrant.
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    h, w = img.shape[:2]
    min_line_len = max(20, w // 12)
    h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (min_line_len, 1))
    h_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, h_kernel)

    v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, h // 8))
    table_mask = cv2.dilate(h_lines, v_kernel)

    contours, _ = cv2.findContours(table_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    img_area = h * w
    best, best_score = None, -1

    for cnt in contours:
        cx, cy, cw, ch = cv2.boundingRect(cnt)
        area = cw * ch
        if area < 0.005 * img_area:
            continue
        center_y = (cy + ch / 2) / h
        center_x = (cx + cw / 2) / w
        score = center_y * 0.5 + center_x * 0.3 + (area / img_area) * 0.2
        if score > best_score:
            best_score = score
            best = (cx, cy, cw, ch)

    if best is None:
        return img[h // 2:, w // 2:]

    cx, cy, cw, ch = best
    pad = 15
    return img[max(0, cy - pad): min(h, cy + ch + pad),
               max(0, cx - pad): min(w, cx + cw + pad)]


def _classify_number(v: float) -> str:
    """Return which coordinate column this value likely belongs to."""
    if _NORTHING_MIN <= v <= _NORTHING_MAX:
        return "northing"
    if _NORTHING_TRUNC_MIN <= v <= _NORTHING_TRUNC_MAX:
        return "northing_trunc"  # OCR dropped last digit
    if _EASTING_MIN <= v <= _EASTING_MAX:
        return "easting"
    if _EDGE_MIN <= v <= _EDGE_MAX and "." in str(v):  # small decimal = edge
        return "edge"
    return "unknown"


def _parse_with_columns(data: dict) -> list[dict]:
    """
    Use bounding-box x-positions to assign words to table columns,
    then group numbers in the same row into coordinate tuples.
    """
    words = []
    for i, text in enumerate(data["text"]):
        text = text.strip()
        if not text or data["conf"][i] == -1:
            continue
        x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
        words.append({"text": text, "x": x, "y": y, "w": w, "h": h})

    if not words:
        return []

    # Determine column boundaries by clustering x-coordinates
    xs = sorted(set(w["x"] for w in words))
    if len(xs) < 2:
        return []

    # Use 4 columns (point, northing, easting, edge)
    # Split x range into 4 equal zones
    x_min, x_max = xs[0], max(w["x"] + w["w"] for w in words)
    col_width = (x_max - x_min) / 4

    def col_idx(x):
        return min(3, int((x - x_min) / col_width))

    # Group words into (row_group, col) using y-coordinate clusters
    # Row height estimate: median height of words
    heights = [w["h"] for w in words if w["h"] > 2]
    row_h = int(np.median(heights)) if heights else 20

    rows_by_y: dict[int, list] = {}
    for w in words:
        row_key = w["y"] // row_h
        rows_by_y.setdefault(row_key, []).append(w)

    # Extract one coordinate tuple per data row
    result = []
    for row_key in sorted(rows_by_y):
        row_words = sorted(rows_by_y[row_key], key=lambda ww: ww["x"])
        cols: dict[int, list[str]] = {}
        for ww in row_words:
            ci = col_idx(ww["x"])
            cols.setdefault(ci, []).append(ww["text"])

        col_text = {ci: " ".join(tokens) for ci, tokens in cols.items()}

        # We need at least columns 1 (northing) and 2 (easting)
        northing = None
        easting = None
        edge = None

        for ci, text in col_text.items():
            v = _to_float(text)
            if v is None:
                continue
            cls = _classify_number(v)
            if cls == "northing" and ci <= 2:
                northing = v
            elif cls == "northing_trunc" and ci <= 2:
                northing = v * 10  # restore truncated last digit (approximate)
            elif cls == "easting" and ci >= 1:
                easting = v
            elif cls == "edge" and ci >= 2:
                edge = v

        if northing is not None and easting is not None:
            result.append({
                "point": len(result) + 1,
                "northing": northing,
                "easting": easting,
                "edge_m": edge,
            })

    return result


def _parse_fallback_regex(text: str) -> list[dict]:
    """
    Fallback: scan full OCR text for numbers, classify by magnitude.

    VN2000 southward zone ranges (Ho Chi Minh City area):
      northing: 7 digits, ~1,200,000–1,300,000
      easting:  6 digits, ~580,000–590,000

    Tesseract commonly:
      - truncates northing to 5-6 digits (1214325 → 12143 or 121432)
      - misreads leading '5' in easting as š/$/&/S/x/# → 82047.83 instead of 582047.83
      - drops the decimal in easting → 58207 instead of 58207x.xx
    """
    # Fix common l→1 / I→1 substitutions before any extraction
    text = text.replace("l2", "12").replace("l1", "11")  # l before digit → 1
    text = re.sub(r"\bI(\d)", r"1\1", text)

    northings: list[float] = []
    eastings: list[float] = []
    edges: list[float] = []

    # --- Northings: 5-7 digit sequences starting with 12 ---
    for m in re.finditer(r"\b12[0-9]{3,5}\b", text):
        raw = m.group(0)
        try:
            v = float(raw)
        except ValueError:
            continue
        if 12_000 <= v <= 13_000:       # 5 digits, last 2 truncated: ×100
            northings.append(v * 100)
        elif 120_000 <= v <= 130_000:   # 6 digits, last 1 truncated: ×10
            northings.append(v * 10)
        elif 1_200_000 <= v <= 1_300_000:  # 7 digits (correct)
            northings.append(v)

    # Also try 7-digit northings that passed the ×10 threshold
    for m in re.finditer(r"\b121[0-9]{4}\b", text):
        v = float(m.group(0))
        if 1_210_000 <= v <= 1_219_999 and v not in northings:
            northings.append(v)

    # --- Eastings: recover from OCR noise ---
    # Pattern A: explicit 5+decimal → 582xxx.xx
    for m in re.finditer(r"\b5[89][0-9]{4}[.,]\d{1,2}\b", text):
        v = _to_float(m.group(0))
        if v and 580_000 <= v <= 590_000:
            eastings.append(v)

    # Pattern B: leading-garbage + 82xxx.xx → add 500000
    # Garbage chars: š ($161), $ (\x24), & (\x26), S, s, x, X, #
    for m in re.finditer(r"[Ssxh#$&šŠ]([89][0-9]{4}[.,]\d{1,2})", text):
        v = _to_float(m.group(1))
        if v and 80_000 <= v <= 90_000:
            eastings.append(v + 500_000)

    # Pattern C: 5-digit truncated easting without decimal → 58xxx → ×10 ≈ 58xxxx
    for m in re.finditer(r"\b5[89][0-9]{3}\b", text):
        v = float(m.group(0))
        if 58_000 <= v <= 59_000:
            # Only add if no decimal version already found for this value
            candidate = v * 10
            if not any(abs(e - candidate) < 100 for e in eastings):
                eastings.append(candidate)

    # --- Edge lengths: small decimals (1–500 m) ---
    for m in re.finditer(r"\b(\d{1,3}[.,]\d{2})\b", text):
        v = _to_float(m.group(1))
        if v and 0.5 <= v <= 500:
            edges.append(v)

    n = min(len(northings), len(eastings))
    if n < 3:
        return []

    # Deduplicate: remove closing point (last == first within 5 m)
    if n > 3 and abs(northings[n-1] - northings[0]) < 5 and abs(eastings[n-1] - eastings[0]) < 5:
        n -= 1

    return [
        {
            "point": i + 1,
            "northing": northings[i],
            "easting": eastings[i],
            "edge_m": edges[i] if i < len(edges) else None,
        }
        for i in range(n)
    ]


def _rows_to_vertices(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    """
    Convert VN2000 coordinates to normalised 0-1 display vertices.
    VN2000: X = northing (N↑), Y = easting (E→).
    Screen: x increases east, y increases south (northing inverted).
    """
    eastings = [r["easting"] for r in rows]
    northings = [r["northing"] for r in rows]

    e_min, e_max = min(eastings), max(eastings)
    n_min, n_max = min(northings), max(northings)
    span = max(e_max - e_min, n_max - n_min)
    if span < 1:
        span = 1

    vertices = [
        {
            "x": round((r["easting"] - e_min) / span, 4),
            "y": round((n_max - r["northing"]) / span, 4),
        }
        for r in rows
    ]

    edges = [
        {
            "from": i,
            "to": (i + 1) % len(rows),
            "length_m": rows[i]["edge_m"],
            "confidence": 0.9 if rows[i]["edge_m"] is not None else 0.0,
        }
        for i in range(len(rows))
    ]

    return vertices, edges


def extract_from_coordinate_table(img: np.ndarray) -> dict:
    """
    Main entry point. Returns vertices/edges in normalised 0-1 space plus raw VN2000 coords.
    Returns {'vertices': [], 'confidence': 0} on failure.
    """
    table_region = _locate_table_region(img)
    pil_img = _preprocess_for_ocr(table_region)

    # Use image_to_data for bounding-box column detection
    tsv_data = pytesseract.image_to_data(
        pil_img,
        lang=TESSERACT_LANG,
        config="--psm 6 --oem 3",
        output_type=pytesseract.Output.DICT,
    )

    rows = _parse_with_columns(tsv_data)

    # Fallback to plain-text regex if column detection found too few rows
    if len(rows) < 3:
        plain_text = pytesseract.image_to_string(
            pil_img, lang=TESSERACT_LANG, config="--psm 6 --oem 3"
        )
        rows = _parse_fallback_regex(plain_text)
        if len(rows) < 3:
            return {
                "vertices": [],
                "confidence": 0.0,
                "vertex_count": 0,
                "source": "coordinate_table",
                "_ocr_text": plain_text,
            }

    vertices, edges = _rows_to_vertices(rows)
    confidence = round(min(1.0, 0.5 + len(rows) * 0.1), 2)

    return {
        "vertices": vertices,
        "edges": edges,
        "confidence": confidence,
        "vertex_count": len(vertices),
        "source": "coordinate_table",
        "coordinates_vn2000": rows,
    }
