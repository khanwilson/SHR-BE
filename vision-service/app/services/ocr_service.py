import asyncio
from concurrent.futures import ThreadPoolExecutor

import cv2
import numpy as np
import pytesseract
from PIL import Image

from app.config import TESSERACT_LANG

_executor = ThreadPoolExecutor(max_workers=2)


async def extract_text(image_bytes: bytes) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, _run_tesseract, image_bytes)


def _run_tesseract(image_bytes: bytes) -> str:
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        return ""

    # Convert to PIL for pytesseract
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(rgb)

    text = pytesseract.image_to_string(
        pil_img,
        lang=TESSERACT_LANG,
        config="--oem 3 --psm 3",  # PSM 3 = automatic page segmentation
    )
    return text.strip()
