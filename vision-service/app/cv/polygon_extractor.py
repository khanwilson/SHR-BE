"""
Detect the main parcel polygon from the diagram region.

Two strategies tried in order:
  1. Hough Lines — find long straight edges, compute intersections.
     Works well for clean hand-drawn diagrams with labeled edges.
  2. Contour fallback — morphological gradient + connected-component
     filtering. Catches irregular / freehand parcels.
"""

import math
import itertools

import cv2
import numpy as np


# ─── helpers ────────────────────────────────────────────────────────────────

def _line_intersection(l1, l2):
    """Return (x, y) intersection of two infinite lines, or None if parallel."""
    x1, y1, x2, y2 = l1
    x3, y3, x4, y4 = l2
    denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(denom) < 1e-6:
        return None
    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
    x = x1 + t * (x2 - x1)
    y = y1 + t * (y2 - y1)
    return (x, y)


def _merge_similar_lines(lines, angle_tol_deg=10, dist_tol_px=20):
    """
    Cluster nearly-parallel, nearly-collinear line segments into one
    representative line each.  Returns list of (x1,y1,x2,y2) tuples.
    """
    if not lines:
        return []

    def line_angle(l):
        x1, y1, x2, y2 = l
        return math.degrees(math.atan2(y2 - y1, x2 - x1)) % 180

    def line_midpoint(l):
        return ((l[0] + l[2]) / 2, (l[1] + l[3]) / 2)

    def pt_to_line_dist(px, py, x1, y1, x2, y2):
        dx, dy = x2 - x1, y2 - y1
        if dx == dy == 0:
            return math.hypot(px - x1, py - y1)
        t = ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)
        t = max(0, min(1, t))
        return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))

    used = [False] * len(lines)
    groups = []
    for i, li in enumerate(lines):
        if used[i]:
            continue
        group = [li]
        used[i] = True
        ai = line_angle(li)
        for j, lj in enumerate(lines):
            if used[j]:
                continue
            aj = line_angle(lj)
            angle_diff = min(abs(ai - aj), 180 - abs(ai - aj))
            if angle_diff > angle_tol_deg:
                continue
            mx, my = line_midpoint(lj)
            if pt_to_line_dist(mx, my, *li) <= dist_tol_px:
                group.append(lj)
                used[j] = True
        groups.append(group)

    merged = []
    for g in groups:
        pts = [(x, y) for x1, y1, x2, y2 in g for x, y in [(x1, y1), (x2, y2)]]
        # Fit a line through all points
        pts_arr = np.array(pts, dtype=np.float32)
        vx, vy, cx, cy = cv2.fitLine(pts_arr, cv2.DIST_L2, 0, 0.01, 0.01).flatten()
        # Extend to bounding box extremes
        t_vals = [(x - cx) / vx if abs(vx) > 1e-6 else (y - cy) / vy
                  for x, y in pts]
        t_min, t_max = min(t_vals), max(t_vals)
        merged.append((
            cx + t_min * vx, cy + t_min * vy,
            cx + t_max * vx, cy + t_max * vy,
        ))
    return merged


def _order_polygon(pts):
    """Sort points in clockwise order around their centroid."""
    cx = sum(p[0] for p in pts) / len(pts)
    cy = sum(p[1] for p in pts) / len(pts)
    return sorted(pts, key=lambda p: math.atan2(p[1] - cy, p[0] - cx))


# ─── Strategy 1: Hough Lines ────────────────────────────────────────────────

def _hough_polygon(diagram: np.ndarray) -> dict:
    """
    Detect polygon by finding long straight lines and computing their
    pairwise intersections.  Filters intersections that lie inside the
    diagram bounds; clusters nearby points into single vertices.
    """
    h, w = diagram.shape[:2]

    # Skip the top strip — it typically contains a section-title text line
    # ("III. Sơ đồ thửa đất…") that Hough picks up as a long horizontal line.
    top_skip = int(h * 0.08)
    working = diagram[top_skip:, :]
    wh, ww = working.shape[:2]

    gray = cv2.cvtColor(working, cv2.COLOR_BGR2GRAY)

    # Isolate dark ink lines: mask out lighter regions (watermarks, stamps, background)
    # before edge detection so the parcel boundary — which is dark printed ink — dominates.
    _, dark_mask = cv2.threshold(gray, 160, 255, cv2.THRESH_BINARY_INV)
    masked = cv2.bitwise_and(gray, gray, mask=dark_mask)

    edges = cv2.Canny(masked, 80, 200, apertureSize=3)

    # Minimum line length: at least 10 % of the shorter image dimension.
    # maxLineGap=20 helps bridge small gaps in lightly-inked edges.
    # Use working-image dimensions for all Hough / filtering steps
    min_len = max(35, int(min(wh, ww) * 0.10))
    raw = cv2.HoughLinesP(edges, 1, math.pi / 180,
                          threshold=40, minLineLength=min_len, maxLineGap=20)
    if raw is None:
        return {"vertices": [], "confidence": 0.0, "vertex_count": 0}

    lines = [tuple(map(float, seg[0])) for seg in raw]

    # Keep lines between min_len and max_len.
    # max_len=40% of the longer dimension eliminates watermark / stamp lines.
    max_len = max(wh, ww) * 0.40
    lines = [l for l in lines
             if min_len <= math.hypot(l[2] - l[0], l[3] - l[1]) <= max_len]

    # Discard lines that hug the working-image border (diagram frame box).
    border_px = max(8, int(min(wh, ww) * 0.04))

    def _on_border(x1, y1, x2, y2):
        if abs(y1 - y2) < 8 and (
                max(y1, y2) < border_px or min(y1, y2) > wh - border_px):
            return True
        if abs(x1 - x2) < 8 and (
                max(x1, x2) < border_px or min(x1, x2) > ww - border_px):
            return True
        return False

    lines = [l for l in lines if not _on_border(*l)]
    if len(lines) < 3:
        return {"vertices": [], "confidence": 0.0, "vertex_count": 0}

    # Merge nearly-parallel / collinear segments
    merged = _merge_similar_lines(lines, angle_tol_deg=15, dist_tol_px=20)
    if len(merged) < 3:
        return {"vertices": [], "confidence": 0.0, "vertex_count": 0}

    # Compute all pairwise intersections inside working image bounds + padding
    pad = 0.05
    intersections = []
    for l1, l2 in itertools.combinations(merged, 2):
        pt = _line_intersection(l1, l2)
        if pt is None:
            continue
        x, y = pt
        if (-pad * ww <= x <= (1 + pad) * ww
                and -pad * wh <= y <= (1 + pad) * wh):
            intersections.append((x, y))

    if len(intersections) < 3:
        return {"vertices": [], "confidence": 0.0, "vertex_count": 0}

    # Cluster nearby intersection points (within 4 % of working width)
    cluster_dist = ww * 0.04
    used = [False] * len(intersections)
    vertices_raw = []
    for i, pt in enumerate(intersections):
        if used[i]:
            continue
        cluster = [pt]
        used[i] = True
        for j in range(i + 1, len(intersections)):
            if not used[j] and math.hypot(pt[0] - intersections[j][0],
                                          pt[1] - intersections[j][1]) < cluster_dist:
                cluster.append(intersections[j])
                used[j] = True
        cx = sum(p[0] for p in cluster) / len(cluster)
        cy = sum(p[1] for p in cluster) / len(cluster)
        vertices_raw.append((cx, cy))

    if len(vertices_raw) < 3:
        return {"vertices": [], "confidence": 0.0, "vertex_count": 0}

    # Convex hull to get a clean polygon (removes noise points inside)
    pts_arr = np.array(vertices_raw, dtype=np.float32)
    hull_idx = cv2.convexHull(pts_arr, returnPoints=False)
    hull_pts = [vertices_raw[i[0]] for i in hull_idx]

    if len(hull_pts) < 3 or len(hull_pts) > 16:
        return {"vertices": [], "confidence": 0.0, "vertex_count": 0}

    # Sanity: hull > 85 % of working area = still detecting the frame, not the parcel
    pre_area = cv2.contourArea(np.array(hull_pts, dtype=np.float32))
    if pre_area / (wh * ww) > 0.85:
        return {"vertices": [], "confidence": 0.0, "vertex_count": 0}

    # Deduplicate hull points that are too close (within 5 % of working width)
    dedup_dist = ww * 0.05
    final_hull = []
    for pt in hull_pts:
        if all(math.hypot(pt[0] - q[0], pt[1] - q[1]) >= dedup_dist for q in final_hull):
            final_hull.append(pt)
    if len(final_hull) < 3:
        return {"vertices": [], "confidence": 0.0, "vertex_count": 0}
    hull_pts = final_hull

    # Normalise to full-diagram 0-1 coordinates (y coords need top_skip offset)
    vertices = [
        {"x": round(max(0.0, min(1.0, x / ww)), 4),
         "y": round(max(0.0, min(1.0, (y + top_skip) / h)), 4)}
        for x, y in _order_polygon(hull_pts)
    ]

    # Confidence based on hull area fraction relative to full diagram
    hull_area = cv2.contourArea(np.array([[p["x"] * w, p["y"] * h]
                                          for p in vertices], dtype=np.float32))
    diagram_area = h * w
    area_frac = hull_area / diagram_area if diagram_area > 0 else 0
    confidence = round(min(0.9, 0.4 + area_frac * 1.5 + len(hull_pts) * 0.02), 3)

    return {
        "vertices": vertices,
        "confidence": confidence,
        "vertex_count": len(vertices),
        "area_fraction": round(area_frac, 3),
    }


# ─── Strategy 2: Contour fallback ───────────────────────────────────────────

def _contour_polygon(diagram: np.ndarray) -> dict:
    gray = cv2.cvtColor(diagram, cv2.COLOR_BGR2GRAY)

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    gradient = cv2.subtract(cv2.dilate(gray, kernel), cv2.erode(gray, kernel))
    _, binary = cv2.threshold(gradient, 30, 255, cv2.THRESH_BINARY)

    min_cc_area = int((diagram.shape[0] + diagram.shape[1]) * 0.3)
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary)
    clean = np.zeros_like(binary)
    for lbl in range(1, num_labels):
        if stats[lbl, cv2.CC_STAT_AREA] >= min_cc_area:
            clean[labels == lbl] = 255

    close_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    closed = cv2.morphologyEx(clean, cv2.MORPH_CLOSE, close_kernel)
    contours, _ = cv2.findContours(closed, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        return {"vertices": [], "confidence": 0.0, "vertex_count": 0}

    diagram_area = diagram.shape[0] * diagram.shape[1]
    candidates = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if not (0.04 * diagram_area < area < 0.85 * diagram_area):
            continue
        epsilon = 0.02 * cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, epsilon, True)
        if not (3 <= len(approx) <= 16):
            continue
        hull = cv2.convexHull(cnt)
        hull_area = cv2.contourArea(hull)
        solidity = area / hull_area if hull_area > 0 else 0
        if solidity < 0.55:
            continue
        perimeter = cv2.arcLength(cnt, True)
        circularity = (4 * 3.14159 * area / (perimeter ** 2)) if perimeter > 0 else 0
        if circularity > 0.75:
            continue
        candidates.append({"approx": approx, "area": area, "solidity": solidity})

    if not candidates:
        return {"vertices": [], "confidence": 0.0, "vertex_count": 0}

    best = max(candidates, key=lambda c: c["area"] * c["solidity"])
    h, w = diagram.shape[:2]
    vertices = [
        {"x": round(float(pt[0][0]) / w, 4), "y": round(float(pt[0][1]) / h, 4)}
        for pt in best["approx"]
    ]
    return {
        "vertices": vertices,
        "confidence": round(min(1.0, best["solidity"]), 3),
        "vertex_count": len(vertices),
        "area_fraction": round(best["area"] / diagram_area, 3),
    }


# ─── Public API ─────────────────────────────────────────────────────────────

def extract_parcel_polygon(diagram: np.ndarray) -> dict:
    """
    Try Hough-Lines first (accurate for clean straight-edged parcels),
    then contour detection.  When Hough finds only 3 vertices (minimum polygon)
    also run contour and keep whichever result has higher confidence.
    """
    hough = _hough_polygon(diagram)
    hough_n = len(hough.get("vertices", []))

    if hough_n >= 4:
        hough["method"] = "hough_lines"
        return hough

    contour = _contour_polygon(diagram)
    contour_n = len(contour.get("vertices", []))

    # If Hough gave exactly 3 vertices, compare confidence with contour
    if hough_n == 3 and contour_n >= 3:
        if contour.get("confidence", 0) > hough.get("confidence", 0):
            contour["method"] = "contour"
            return contour
        hough["method"] = "hough_lines"
        return hough

    if contour_n >= 3:
        contour["method"] = "contour"
        return contour

    if hough_n >= 3:
        hough["method"] = "hough_lines"
        return hough

    # Nothing found
    contour["method"] = "contour"
    return contour
