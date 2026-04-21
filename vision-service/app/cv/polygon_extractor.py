"""
Detect the main parcel polygon from the diagram region.

Strategy:
1. Use morphological gradient to isolate thick lines (parcel boundary ~2-4px)
   vs thin strokes (text ~1px).
2. Remove small connected components (individual text characters).
3. Close gaps in the boundary.
4. Find contours, score by area * solidity.
5. Approximate polygon with approxPolyDP.
"""

import cv2
import numpy as np


def extract_parcel_polygon(diagram: np.ndarray) -> dict:
    gray = cv2.cvtColor(diagram, cv2.COLOR_BGR2GRAY)

    # Morphological gradient: highlights edges proportional to line thickness
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    dilated = cv2.dilate(gray, kernel, iterations=1)
    eroded = cv2.erode(gray, kernel, iterations=1)
    gradient = cv2.subtract(dilated, eroded)

    _, binary = cv2.threshold(gradient, 30, 255, cv2.THRESH_BINARY)

    # Remove small connected components (text characters)
    # Minimum size: roughly the perimeter of the whole diagram
    min_cc_area = int((diagram.shape[0] + diagram.shape[1]) * 1.5)
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary)

    clean = np.zeros_like(binary)
    for lbl in range(1, num_labels):
        if stats[lbl, cv2.CC_STAT_AREA] >= min_cc_area:
            clean[labels == lbl] = 255

    # Close small gaps in the polygon outline
    close_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    closed = cv2.morphologyEx(clean, cv2.MORPH_CLOSE, close_kernel)

    contours, _ = cv2.findContours(closed, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        return {"vertices": [], "confidence": 0.0, "vertex_count": 0}

    diagram_area = diagram.shape[0] * diagram.shape[1]
    candidates = []

    for cnt in contours:
        area = cv2.contourArea(cnt)
        # Main parcel polygon occupies 15-85% of the diagram area
        if not (0.15 * diagram_area < area < 0.85 * diagram_area):
            continue

        # Approximate with 1.5% of perimeter as epsilon
        epsilon = 0.015 * cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, epsilon, True)

        # Vietnamese land parcels typically have 3-12 vertices
        if not (3 <= len(approx) <= 12):
            continue

        # Solidity: ratio of contour area to convex hull area
        # Very concave shapes (< 0.6) are likely noise
        hull = cv2.convexHull(cnt)
        hull_area = cv2.contourArea(hull)
        solidity = area / hull_area if hull_area > 0 else 0
        if solidity < 0.55:
            continue

        candidates.append({
            "approx": approx,
            "area": area,
            "solidity": solidity,
        })

    if not candidates:
        return {"vertices": [], "confidence": 0.0, "vertex_count": 0}

    # Best candidate: largest area weighted by solidity
    best = max(candidates, key=lambda c: c["area"] * c["solidity"])
    h, w = diagram.shape[:2]

    vertices = [
        {"x": round(float(pt[0][0]) / w, 4), "y": round(float(pt[0][1]) / h, 4)}
        for pt in best["approx"]
    ]

    confidence = round(min(1.0, best["solidity"]), 3)

    return {
        "vertices": vertices,
        "confidence": confidence,
        "vertex_count": len(vertices),
        "area_fraction": round(best["area"] / diagram_area, 3),
    }
