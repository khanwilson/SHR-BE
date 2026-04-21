from fastapi import APIRouter, File, HTTPException, UploadFile

from app.services.parcel_service import process_parcel_image

router = APIRouter()


@router.post("/extract")
async def extract(image: UploadFile = File(...)):
    if image.content_type not in ("image/jpeg", "image/jpg", "image/png"):
        raise HTTPException(422, "Only JPEG/PNG accepted")

    image_bytes = await image.read()
    if len(image_bytes) > 20 * 1024 * 1024:
        raise HTTPException(413, "Image too large (max 20MB)")

    result = await process_parcel_image(image_bytes)
    return result
