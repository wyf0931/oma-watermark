"""FastAPI application for the watermark remover."""

from __future__ import annotations

import base64
import sys
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .core import (
    DEFAULT_EXPAND,
    DEFAULT_THRESHOLD,
    InvalidImageError,
    InvalidRoiError,
    NoWatermarkDetectedError,
    Roi,
    decode_image,
    encode_image,
    remove_watermark,
)
from .lama import AIInpaintingError, AIModelUnavailableError, model_available

BASE_DIR = Path(__file__).resolve().parent


def _static_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", BASE_DIR)) / "oma_watermark" / "static"
    return BASE_DIR / "static"


STATIC_DIR = _static_dir()
MAX_UPLOAD_BYTES = 25 * 1024 * 1024

app = FastAPI(title="水印清除器", version="0.1.2")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def _data_url(data: bytes, mime_type: str) -> str:
    return f"data:{mime_type};base64,{base64.b64encode(data).decode('ascii')}"


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health() -> dict[str, object]:
    return {
        "status": "ok",
        "ai_available": model_available(),
        "ai_engine": "LaMa 512 (OpenCV DNN)",
    }


@app.post("/api/remove")
def remove(
    file: UploadFile = File(...),
    x: int = Form(...),
    y: int = Form(...),
    width: int = Form(...),
    height: int = Form(...),
    threshold: int = Form(DEFAULT_THRESHOLD),
    expand: int = Form(DEFAULT_EXPAND),
    mode: str = Form("ai"),
) -> dict[str, object]:
    if mode not in {"fast", "ai"}:
        raise HTTPException(status_code=422, detail="修复模式必须是 fast 或 ai")

    data = file.file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="图片不能超过 25 MB")

    try:
        image, source_format = decode_image(data)
        roi = Roi(x=x, y=y, width=width, height=height)
        result = remove_watermark(
            image,
            roi,
            threshold=threshold,
            expand=expand,
            engine=mode,
        )
    except (InvalidImageError, InvalidRoiError, NoWatermarkDetectedError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except AIModelUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except AIInpaintingError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
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
        "mode": result.engine,
        "expand": expand,
        "roi": {
            "x": roi.x,
            "y": roi.y,
            "width": roi.width,
            "height": roi.height,
        },
    }
