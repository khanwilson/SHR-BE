import cv2
import numpy as np

from app.config import MAX_IMAGE_DIMENSION


def decode_image(image_bytes: bytes) -> np.ndarray:
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Failed to decode image")
    return img


def resize_for_processing(img: np.ndarray) -> np.ndarray:
    h, w = img.shape[:2]
    max_dim = max(h, w)
    if max_dim <= MAX_IMAGE_DIMENSION:
        return img
    scale = MAX_IMAGE_DIMENSION / max_dim
    return cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)


def encode_image_base64(img: np.ndarray) -> str:
    import base64
    _, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return base64.b64encode(buf.tobytes()).decode("utf-8")


def deskew_region(region: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    lines = cv2.HoughLinesP(
        edges, 1, np.pi / 180, threshold=80,
        minLineLength=region.shape[1] * 0.25, maxLineGap=20,
    )
    if lines is None:
        return region

    angles = []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
        if abs(angle) < 45:
            angles.append(angle)

    if not angles:
        return region

    median_angle = float(np.median(angles))
    if abs(median_angle) < 0.5:
        return region

    h, w = region.shape[:2]
    M = cv2.getRotationMatrix2D((w // 2, h // 2), median_angle, 1.0)
    return cv2.warpAffine(region, M, (w, h), borderMode=cv2.BORDER_REPLICATE)
