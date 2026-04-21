"""
Extract edge length measurements from the diagram by running OCR on
the region near each edge's midpoint.

Vietnamese sổ hồng uses comma as decimal separator (e.g. "12,5m").
"""

import re

import cv2
import numpy as np
import pytesseract
from PIL import Image

from app.config import TESSERACT_LANG

_MEASUREMENT_RE = re.compile(r"(\d+[,\.]\d+|\d+)\s*m\b", re.IGNORECASE)


def extract_edge_measurements(
    diagram: np.ndarray,
    vertices: list[dict],
) -> list[dict]:
    h, w = diagram.shape[:2]
    n = len(vertices)
    edges = []

    for i in range(n):
        v1 = vertices[i]
        v2 = vertices[(i + 1) % n]

        x1, y1 = int(v1["x"] * w), int(v1["y"] * h)
        x2, y2 = int(v2["x"] * w), int(v2["y"] * h)

        length_m, raw_text = _ocr_edge_region(diagram, x1, y1, x2, y2)
        edges.append({
            "from": i,
            "to": (i + 1) % n,
            "length_m": length_m,
            "raw_text": raw_text,
            "confidence": 0.85 if length_m is not None else 0.0,
        })

    return edges


def _ocr_edge_region(
    diagram: np.ndarray,
    x1: int, y1: int, x2: int, y2: int,
) -> tuple[float | None, str]:
    h, w = diagram.shape[:2]
    margin = 70

    # Bounding box around the edge with margin
    rx1 = max(0, min(x1, x2) - margin)
    ry1 = max(0, min(y1, y2) - margin)
    rx2 = min(w, max(x1, x2) + margin)
    ry2 = min(h, max(y1, y2) + margin)

    roi = diagram[ry1:ry2, rx1:rx2]
    if roi.size == 0:
        return None, ""

    # Rotate ROI so the edge is horizontal
    angle_deg = np.degrees(np.arctan2(y2 - y1, x2 - x1))
    roi_h, roi_w = roi.shape[:2]
    M = cv2.getRotationMatrix2D((roi_w // 2, roi_h // 2), angle_deg, 1.0)
    rotated = cv2.warpAffine(roi, M, (roi_w, roi_h))

    # Crop a horizontal strip (±50px around the edge center)
    cx = roi_w // 2
    cy = roi_h // 2
    strip = rotated[max(0, cy - 50):min(roi_h, cy + 50), :]

    # Upscale 3x for better OCR accuracy
    scale = 3
    strip_up = cv2.resize(strip, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

    # Binarize
    gray = cv2.cvtColor(strip_up, cv2.COLOR_BGR2GRAY)
    _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    pil_img = Image.fromarray(bw)
    ocr_text = pytesseract.image_to_string(
        pil_img,
        lang=TESSERACT_LANG,
        config="--psm 7 --oem 3",  # PSM 7 = single text line
    ).strip()

    match = _MEASUREMENT_RE.search(ocr_text)
    if match:
        raw_num = match.group(1).replace(",", ".")
        try:
            return float(raw_num), ocr_text
        except ValueError:
            pass

    return None, ocr_text
