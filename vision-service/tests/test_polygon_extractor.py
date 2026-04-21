"""Basic unit tests for polygon extractor."""

import numpy as np
import pytest


def make_rectangle_diagram(width=400, height=400, rect_x=80, rect_y=80, rect_w=240, rect_h=200):
    """Create a synthetic diagram with a rectangle drawn on white background."""
    img = np.ones((height, width, 3), dtype=np.uint8) * 255
    # Draw thick rectangle (parcel boundary)
    color = (0, 0, 0)
    thickness = 3
    cv2 = pytest.importorskip("cv2")
    cv2.rectangle(img, (rect_x, rect_y), (rect_x + rect_w, rect_y + rect_h), color, thickness)
    return img


def test_extract_rectangle():
    cv2 = pytest.importorskip("cv2")
    from app.cv.polygon_extractor import extract_parcel_polygon  # noqa: PLC0415

    img = make_rectangle_diagram()
    result = extract_parcel_polygon(img)

    assert result["vertex_count"] >= 3, "Should detect polygon vertices"
    assert result["confidence"] > 0.5, "Confidence should be reasonable for clear rectangle"
    assert len(result["vertices"]) >= 3


def test_no_polygon_on_blank():
    pytest.importorskip("cv2")
    import numpy as np  # noqa: PLC0415
    from app.cv.polygon_extractor import extract_parcel_polygon  # noqa: PLC0415

    blank = np.ones((400, 400, 3), dtype=np.uint8) * 255
    result = extract_parcel_polygon(blank)
    assert result["vertices"] == []
    assert result["confidence"] == 0.0
