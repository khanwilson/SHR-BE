from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import health, ocr, parcel

app = FastAPI(title="SHR Vision Service", version="1.0.0")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(ocr.router, prefix="/ocr", tags=["ocr"])
app.include_router(parcel.router, prefix="/parcel", tags=["parcel"])
