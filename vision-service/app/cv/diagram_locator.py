"""
Locate the parcel diagram region within a sổ hồng page.

Two common layouts:
  A) Separate diagram page — diagram fills most of the page.
  B) Single page — left half is certificate text, right half is diagram (Section III).

Strategy:
  1. Contour-based detection with broad area range (3–50 % of page).
     Prefer right-side, upper candidates.
  2. If no good candidate found, scan multiple fixed regions and pick the one
     where the polygon extractor finds the best result (most plausible long lines).
  3. Ultimate fallback: upper-right 60 % × 65 % crop.
"""

import math

import cv2
import numpy as np


def _long_line_density(region: np.ndarray) -> float:
    """
    Proxy for 'how much does this region look like a diagram':
    ratio of long-line pixels to total pixels.
    A region with a drawn polygon has many long connected edges;
    a text-only region has only short strokes.
    """
    gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    lines = cv2.HoughLinesP(edges, 1, math.pi / 180,
                            threshold=40, minLineLength=40, maxLineGap=8)
    if lines is None:
        return 0.0
    total_len = sum(
        math.hypot(x2 - x1, y2 - y1)
        for x1, y1, x2, y2 in lines[:, 0]
    )
    area = region.shape[0] * region.shape[1]
    return total_len / area if area > 0 else 0.0


def locate_diagram_region(img: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    img_h, img_w = img.shape[:2]
    img_area = img_h * img_w
    candidates = []

    for cnt in contours:
        area = cv2.contourArea(cnt)
        # Broad range: 3 % (small coordinate-table box) to 50 % (half-page diagram)
        if not (0.03 * img_area < area < 0.50 * img_area):
            continue

        epsilon = 0.02 * cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, epsilon, True)
        if len(approx) not in range(4, 9):
            continue

        x, y, w, h = cv2.boundingRect(cnt)
        if h == 0:
            continue
        aspect = w / h
        if not (0.3 < aspect < 3.0):
            continue

        # Reject candidates that span nearly the full image — these are the
        # overall certificate body, not a specific diagram box.
        if w > 0.80 * img_w or h > 0.80 * img_h:
            continue

        cx_ratio = (x + w / 2) / img_w          # 0 = left edge, 1 = right edge
        cy_ratio = (y + h / 2) / img_h           # 0 = top, 1 = bottom
        area_ratio = area / img_area

        score = (cx_ratio * 0.4              # prefer right side
                 + (1 - cy_ratio) * 0.2      # slight preference for upper
                 + area_ratio * 0.4)         # prefer larger regions

        candidates.append({
            "bbox": (x, y, w, h),
            "area": area,
            "score": score,
        })

    if candidates:
        best = max(candidates, key=lambda c: c["score"])
        x, y, w, h = best["bbox"]
        pad = 10
        region = img[max(0, y - pad): min(img_h, y + h + pad),
                     max(0, x - pad): min(img_w, x + w + pad)]

        # Accept if the region actually looks like a diagram (has long lines)
        if _long_line_density(region) > 0.015:
            return region

    # Fallback: scan fixed sub-regions and pick the one with the most
    # long-line content (= most likely to be the drawn diagram).
    # Covers both "diagram fills whole page" and "diagram is top-right half".
    sub_regions = [
        # (y_start_frac, y_end_frac, x_start_frac, x_end_frac, label)
        (0.00, 0.65, 0.40, 1.00, "upper-right"),   # single-page layout, top-right
        (0.00, 1.00, 0.40, 1.00, "full-right"),    # right half
        (0.00, 0.60, 0.00, 1.00, "upper-full"),    # top 60 % (separate diagram page)
        (0.00, 1.00, 0.00, 1.00, "full-page"),     # entire page
    ]

    # Try regions from most specific (smallest) to most general.
    # Return the first one whose long-line density exceeds the threshold —
    # this gives the tightest crop that still contains diagram content.
    MIN_DENSITY = 0.008
    for y0f, y1f, x0f, x1f, _ in sub_regions:
        y0, y1 = int(img_h * y0f), int(img_h * y1f)
        x0, x1 = int(img_w * x0f), int(img_w * x1f)
        crop = img[y0:y1, x0:x1]
        if crop.size == 0:
            continue
        if _long_line_density(crop) >= MIN_DENSITY:
            return crop

    # Absolute fallback
    return img[:int(img_h * 0.65), int(img_w * 0.40):]
