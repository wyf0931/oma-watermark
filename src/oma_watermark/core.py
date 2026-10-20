"""OpenCV watermark removal for a user-selected ROI."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO

import cv2
import numpy as np
from PIL import Image, ImageOps

MAX_IMAGE_PIXELS = 30_000_000
DEFAULT_THRESHOLD = 200
DEFAULT_DILATION = 6
INPAINT_RADIUS = 5
MIN_ROI_SIZE = 4

# Fail early on decompression bombs before allocating an oversized array.
Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS


class InvalidImageError(ValueError):
    """The uploaded bytes are not a supported image."""


class InvalidRoiError(ValueError):
    """The requested region does not fit inside the image."""


class NoWatermarkDetectedError(ValueError):
    """No bright pixels were found in the selected region."""


@dataclass(frozen=True)
class Roi:
    x: int
    y: int
    width: int
    height: int

    def validate(self, image_width: int, image_height: int) -> None:
        if self.x < 0 or self.y < 0:
            raise InvalidRoiError("选区坐标不能为负数")
        if self.width < MIN_ROI_SIZE or self.height < MIN_ROI_SIZE:
            raise InvalidRoiError(f"选区太小，宽高至少为 {MIN_ROI_SIZE} 像素")
        if self.x + self.width > image_width or self.y + self.height > image_height:
            raise InvalidRoiError("选区超出了图片范围")


@dataclass
class RemovalResult:
    image: np.ndarray
    mask: np.ndarray
    mask_overlay: np.ndarray
    masked_pixels: int


def decode_image(data: bytes) -> tuple[np.ndarray, str | None]:
    """Decode image bytes to BGR, honoring EXIF orientation and alpha."""
    if not data:
        raise InvalidImageError("图片为空")

    try:
        with Image.open(BytesIO(data)) as source:
            if source.width * source.height > MAX_IMAGE_PIXELS:
                raise InvalidImageError("图片像素过多（上限 3000 万像素）")
            source.load()
            source_format = source.format
            image = ImageOps.exif_transpose(source)

            if image.mode in {"RGBA", "LA"} or "transparency" in image.info:
                rgba = image.convert("RGBA")
                background = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
                rgb = Image.alpha_composite(background, rgba).convert("RGB")
            else:
                rgb = image.convert("RGB")
    except InvalidImageError:
        raise
    except (Image.DecompressionBombError, Image.UnidentifiedImageError, OSError) as exc:
        raise InvalidImageError("无法读取图片，请上传 PNG、JPEG 或 WebP 文件") from exc

    bgr = cv2.cvtColor(np.asarray(rgb), cv2.COLOR_RGB2BGR)
    return bgr, source_format


def encode_image(image: np.ndarray, source_format: str | None = None) -> tuple[bytes, str, str]:
    """Encode an image as JPEG when possible, otherwise PNG."""
    is_jpeg = source_format in {"JPEG", "MPO"}
    extension = ".jpg" if is_jpeg else ".png"
    mime_type = "image/jpeg" if is_jpeg else "image/png"
    params = [cv2.IMWRITE_JPEG_QUALITY, 95] if is_jpeg else [cv2.IMWRITE_PNG_COMPRESSION, 3]
    ok, buffer = cv2.imencode(extension, image, params)
    if not ok:
        raise RuntimeError("图片编码失败")
    return buffer.tobytes(), mime_type, extension


def build_mask(
    image: np.ndarray,
    roi: Roi,
    threshold: int = DEFAULT_THRESHOLD,
    dilation: int = DEFAULT_DILATION,
) -> tuple[np.ndarray, np.ndarray, int]:
    """Select near-white pixels inside the ROI and return a full-size mask."""
    if not 0 <= threshold <= 255:
        raise ValueError("亮度阈值必须在 0 到 255 之间")
    if dilation < 0:
        raise ValueError("膨胀次数不能为负数")

    height, width = image.shape[:2]
    roi.validate(width, height)

    crop = image[roi.y : roi.y + roi.height, roi.x : roi.x + roi.width]
    lower = np.array([threshold, threshold, threshold], dtype=np.uint8)
    mask_crop = cv2.inRange(crop, lower, np.array([255, 255, 255], dtype=np.uint8))

    if dilation:
        # Grow past anti-aliased edges and the usual subtle text shadow.
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        mask_crop = cv2.dilate(mask_crop, kernel, iterations=dilation)

    masked_pixels = int(cv2.countNonZero(mask_crop))
    if masked_pixels == 0:
        raise NoWatermarkDetectedError(
            "选区内没有检测到浅色水印。请重新框选，或调低亮度阈值。"
        )

    mask = np.zeros((height, width), dtype=np.uint8)
    mask[roi.y : roi.y + roi.height, roi.x : roi.x + roi.width] = mask_crop
    return mask, mask_crop, masked_pixels


def make_mask_overlay(image: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Show detected pixels in red over the original image."""
    overlay = image.copy()
    overlay[mask > 0] = (40, 40, 230)
    return cv2.addWeighted(image, 0.35, overlay, 0.65, 0)


def remove_watermark(
    image: np.ndarray,
    roi: Roi,
    threshold: int = DEFAULT_THRESHOLD,
    dilation: int = DEFAULT_DILATION,
) -> RemovalResult:
    """Inpaint bright watermark pixels inside the selected region."""
    mask, _, masked_pixels = build_mask(image, roi, threshold, dilation)
    cleaned = cv2.inpaint(image, mask, INPAINT_RADIUS, cv2.INPAINT_TELEA)
    return RemovalResult(
        image=cleaned,
        mask=mask,
        mask_overlay=make_mask_overlay(image, mask),
        masked_pixels=masked_pixels,
    )
