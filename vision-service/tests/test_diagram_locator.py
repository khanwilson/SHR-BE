"""Basic unit tests for diagram locator."""

import numpy as np
import pytest


def make_page_with_diagram(page_w=1200, page_h=1600):
    """Simulate a sổ hồng page: white background with text boxes and one diagram box."""
    cv2 = pytest.importorskip("cv2")
    img = np.ones((page_h, page_w, 3), dtype=np.uint8) * 255

    # Draw text area boxes (small, upper half)
    for row in range(3):
        for col in range(2):
            x = 80 + col * 500
            y = 80 + row * 120
            cv2.rectangle(img, (x, y), (x + 400, y + 80), (0, 0, 0), 2)

    # Draw diagram box (lower-right area, ~10% of page)
    diagram_x, diagram_y = 700, 900
    diagram_w, diagram_h = 400, 350
    cv2.rectangle(img, (diagram_x, diagram_y),
                  (diagram_x + diagram_w, diagram_y + diagram_h), (0, 0, 0), 4)

    return img, (diagram_x, diagram_y, diagram_w, diagram_h)


def test_locates_diagram_region():
    pytest.importorskip("cv2")
    from app.cv.diagram_locator import locate_diagram_region  # noqa: PLC0415

    page, (dx, dy, dw, dh) = make_page_with_diagram()
    region = locate_diagram_region(page)

    # The returned region should be much smaller than the original page
    assert region.shape[0] < page.shape[0] * 0.6, "Should crop to diagram area"
    assert region.shape[1] < page.shape[1] * 0.6, "Should crop to diagram area"
    assert region.shape[0] > 50, "Region should not be too small"
