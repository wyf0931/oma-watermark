"""FastAPI application for the watermark remover."""

from __future__ import annotations

import base64
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .core import (
    DEFAULT_THRESHOLD,
    InvalidImageError,
    InvalidRoiError,
    NoWatermarkDetectedError,
    Roi,
    decode_image,
    encode_image,
    remove_watermark,
)

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
MAX_UPLOAD_BYTES = 25 * 1024 * 1024

app = FastAPI(title="水印清除器", version="0.1.0")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def _data_url(data: bytes, mime_type: str) -> str:
    return f"data:{mime_type};base64,{base64.b64encode(data).decode('ascii')}"


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/remove")
def remove(
    file: UploadFile = File(...),
    x: int = Form(...),
    y: int = Form(...),
    width: int = Form(...),
    height: int = Form(...),
    threshold: int = Form(DEFAULT_THRESHOLD),
) -> dict[str, object]:
    data = file.file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="图片不能超过 25 MB")

    try:
        image, source_format = decode_image(data)
        roi = Roi(x=x, y=y, width=width, height=height)
        result = remove_watermark(image, roi, threshold=threshold)
    except (InvalidImageError, InvalidRoiError, NoWatermarkDetectedError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    result_bytes, mime_type, extension = encode_image(result.image, source_format)
    overlay_bytes, overlay_mime, _ = encode_image(result.mask_overlay, "PNG")
    source_name = Path(file.filename or "image").stem or "image"
    height_px, width_px = image.shape[:2]

    return {
        "result": _data_url(result_bytes, mime_type),
        "mask_overlay": _data_url(overlay_bytes, overlay_mime),
        "filename": f"cleaned_{source_name}{extension}",
        "width": width_px,
        "height": height_px,
        "detected_pixels": result.masked_pixels,
        "roi": {
            "x": roi.x,
            "y": roi.y,
            "width": roi.width,
            "height": roi.height,
        },
    }
