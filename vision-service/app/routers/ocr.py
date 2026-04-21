from fastapi import APIRouter, File, HTTPException, UploadFile

from app.services.ocr_service import extract_text

router = APIRouter()


@router.post("/extract")
async def extract(image: UploadFile = File(...)):
    if image.content_type not in ("image/jpeg", "image/jpg", "image/png"):
        raise HTTPException(422, "Only JPEG/PNG accepted")

    image_bytes = await image.read()
    if len(image_bytes) > 20 * 1024 * 1024:
        raise HTTPException(413, "Image too large (max 20MB)")

    text = await extract_text(image_bytes)
    return {"text": text, "provider": "tesseract"}
