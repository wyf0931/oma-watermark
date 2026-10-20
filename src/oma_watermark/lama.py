"""Optional LaMa inpainting through OpenCV DNN.

The model is downloaded separately, so OpenCV-only installs keep the fast path.
"""

from __future__ import annotations

import os
import sys
import threading
from pathlib import Path

import cv2
import numpy as np

MODEL_FILENAME = "inpainting_lama_2025jan.onnx"
MODEL_REPO = "opencv/inpainting_lama"
MIN_MODEL_BYTES = 80 * 1024 * 1024
MODEL_INPUT_SIZE = 512
DEFAULT_MODEL_PATH = Path("models") / MODEL_FILENAME
DOWNLOAD_COMMAND = "uv run oma-watermark-download-model"


class AIModelUnavailableError(RuntimeError):
    """The LaMa model is missing or cannot be loaded."""


class AIInpaintingError(RuntimeError):
    """The model is loaded but inference failed."""


def _default_model_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path.cwd())) / "models" / MODEL_FILENAME
    return DEFAULT_MODEL_PATH


def model_path() -> Path:
    configured = os.environ.get("OMA_LAMA_MODEL")
    return Path(configured).expanduser() if configured else _default_model_path()


def model_available() -> bool:
    path = model_path()
    try:
        return path.is_file() and path.stat().st_size >= MIN_MODEL_BYTES
    except OSError:
        return False


class LamaInpainter:
    def __init__(self, path: Path) -> None:
        try:
            self._net = cv2.dnn.readNetFromONNX(str(path))
        except cv2.error as exc:
            raise AIModelUnavailableError(
                f"无法加载 LaMa 模型：{path}。可删除后重新运行 {DOWNLOAD_COMMAND}。"
            ) from exc

    def infer(self, crop: np.ndarray, mask_crop: np.ndarray) -> np.ndarray:
        height, width = crop.shape[:2]
        image_blob = cv2.dnn.blobFromImage(
            crop,
            scalefactor=1.0 / 255.0,
            size=(MODEL_INPUT_SIZE, MODEL_INPUT_SIZE),
            mean=(0, 0, 0),
            swapRB=False,
            crop=False,
        )
        resized_mask = cv2.resize(
            mask_crop,
            (MODEL_INPUT_SIZE, MODEL_INPUT_SIZE),
            interpolation=cv2.INTER_NEAREST,
        )
        mask_blob = (resized_mask > 0).astype(np.float32)[None, None, :, :]

        try:
            self._net.setInput(image_blob, "image")
            self._net.setInput(mask_blob, "mask")
            output = self._net.forward()
            result = output[0].transpose(1, 2, 0)
            result = np.clip(result, 0, 255).astype(np.uint8)
        except (cv2.error, ValueError, IndexError) as exc:
            raise AIInpaintingError(
                "LaMa 推理失败，请尝试缩小选区或改用快速模式。"
            ) from exc

        interpolation = (
            cv2.INTER_AREA if max(height, width) > MODEL_INPUT_SIZE else cv2.INTER_CUBIC
        )
        return cv2.resize(result, (width, height), interpolation=interpolation)


_inpainter: LamaInpainter | None = None
_inpainter_path: Path | None = None
_model_lock = threading.Lock()
_inference_lock = threading.Lock()


def _get_inpainter() -> LamaInpainter:
    global _inpainter, _inpainter_path

    path = model_path()
    if not model_available():
        raise AIModelUnavailableError(
            f"未找到 LaMa 模型。请先运行：{DOWNLOAD_COMMAND}（或设置 OMA_LAMA_MODEL）。"
        )

    with _model_lock:
        if _inpainter is None or _inpainter_path != path:
            _inpainter = LamaInpainter(path)
            _inpainter_path = path
        return _inpainter


def clear_model_cache() -> None:
    """Drop the loaded model, mainly for tests and model replacement."""
    global _inpainter, _inpainter_path

    with _model_lock:
        _inpainter = None
        _inpainter_path = None


def _crop_box(
    height: int, width: int, bbox: tuple[int, int, int, int]
) -> tuple[int, int, int]:
    x1, y1, x2, y2 = bbox
    side = max(x2 - x1, y2 - y1)
    padding = max(32, int(side * 0.15))
    side = min(side + padding * 2, min(height, width))

    center_x = (x1 + x2) // 2
    center_y = (y1 + y2) // 2
    left = max(0, min(width - side, center_x - side // 2))
    top = max(0, min(height - side, center_y - side // 2))
    return left, top, side


def inpaint_with_lama(image: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Inpaint a mask with LaMa using a square crop around the mask."""
    if image.shape[:2] != mask.shape[:2]:
        raise AIInpaintingError("图片和 mask 尺寸不一致。")

    points = cv2.findNonZero(mask)
    if points is None:
        raise AIInpaintingError("没有需要修复的像素。")

    x, y, width, height = cv2.boundingRect(points)
    left, top, side = _crop_box(
        image.shape[0], image.shape[1], (x, y, x + width, y + height)
    )
    crop = image[top : top + side, left : left + side]
    mask_crop = mask[top : top + side, left : left + side]
    inpainter = _get_inpainter()

    with _inference_lock:
        repaired = inpainter.infer(crop, mask_crop)

    result = image.copy()
    target = result[top : top + side, left : left + side]
    target[mask_crop > 0] = repaired[mask_crop > 0]
    return result
