"""
Locate the parcel diagram region within a sổ hồng page.

The diagram is a boxed region (~3-15% of page area) typically in the lower half,
with a thicker border than text boxes.
"""

import cv2
import numpy as np


def locate_diagram_region(img: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    img_area = img.shape[0] * img.shape[1]
    candidates = []

    for cnt in contours:
        area = cv2.contourArea(cnt)
        # Diagram box is 3-15% of total image area
        if not (0.03 * img_area < area < 0.15 * img_area):
            continue

        epsilon = 0.02 * cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, epsilon, True)

        # Should be roughly rectangular (4-6 vertices allow slight perspective warp)
        if len(approx) not in (4, 5, 6):
            continue

        x, y, w, h = cv2.boundingRect(cnt)
        if h == 0:
            continue
        aspect = w / h
        if not (0.5 < aspect < 2.0):
            continue

        # Score: lower on page is better (diagram is usually in lower half)
        center_y_ratio = (y + h / 2) / img.shape[0]
        area_ratio = area / img_area
        rect_score = 1.0 if len(approx) == 4 else 0.6

        candidates.append({
            "bbox": (x, y, w, h),
            "area": area,
            "score": center_y_ratio * 0.4 + area_ratio * 0.4 + rect_score * 0.2,
            "n_vertices": len(approx),
        })

    if not candidates:
        # Fallback: lower-right quadrant of the image
        h, w = img.shape[:2]
        return img[h // 2:, w // 2:]

    best = max(candidates, key=lambda c: c["score"])
    x, y, w, h = best["bbox"]
    pad = 10
    y1 = max(0, y - pad)
    y2 = min(img.shape[0], y + h + pad)
    x1 = max(0, x - pad)
    x2 = min(img.shape[1], x + w + pad)
    return img[y1:y2, x1:x2]
