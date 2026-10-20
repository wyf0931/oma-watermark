import cv2
import numpy as np
import pytest

from oma_watermark.core import (
    NoWatermarkDetectedError,
    Roi,
    build_mask,
    decode_image,
    remove_watermark,
)
from oma_watermark.lama import (
    AIModelUnavailableError,
    clear_model_cache,
    model_available,
)


def make_watermarked_image() -> np.ndarray:
    image = np.full((240, 320, 3), (40, 80, 120), dtype=np.uint8)
    cv2.putText(
        image,
        "AI",
        (100, 150),
        cv2.FONT_HERSHEY_SIMPLEX,
        2.2,
        (255, 255, 255),
        5,
        cv2.LINE_AA,
    )
    return image


def test_removes_detected_pixels_without_touching_outside_roi() -> None:
    image = make_watermarked_image()
    roi = Roi(x=80, y=85, width=180, height=100)

    result = remove_watermark(image, roi, threshold=200)

    assert result.masked_pixels > 0
    assert result.engine == "fast"
    assert result.mask.shape == image.shape[:2]
    assert np.count_nonzero(result.mask[: roi.y]) == 0
    assert np.count_nonzero(result.mask[roi.y + roi.height :]) == 0
    assert np.count_nonzero(result.mask[:, : roi.x]) == 0
    assert np.count_nonzero(result.mask[:, roi.x + roi.width :]) == 0

    outside = result.mask == 0
    assert np.array_equal(result.image[outside], image[outside])
    assert np.any(result.image[result.mask > 0] != image[result.mask > 0])


def test_lower_threshold_selects_more_pixels() -> None:
    image = np.full((80, 80, 3), 180, dtype=np.uint8)
    image[20:40, 20:40] = 220
    roi = Roi(x=0, y=0, width=80, height=80)

    _, _, low_threshold_pixels = build_mask(image, roi, threshold=170, expand=0)
    _, _, high_threshold_pixels = build_mask(image, roi, threshold=210, expand=0)

    assert low_threshold_pixels > high_threshold_pixels


def test_expand_grows_the_mask() -> None:
    image = make_watermarked_image()
    roi = Roi(x=80, y=85, width=180, height=100)

    _, _, tight_pixels = build_mask(image, roi, threshold=200, expand=0)
    _, _, expanded_pixels = build_mask(image, roi, threshold=200, expand=4)

    assert expanded_pixels > tight_pixels


def test_rejects_out_of_range_expand() -> None:
    image = np.zeros((100, 100, 3), dtype=np.uint8)

    with pytest.raises(ValueError, match="边缘扩展"):
        build_mask(image, Roi(x=10, y=10, width=40, height=40), expand=13)


def test_raises_when_roi_contains_no_bright_pixels() -> None:
    image = np.full((80, 80, 3), 100, dtype=np.uint8)

    with pytest.raises(NoWatermarkDetectedError):
        build_mask(image, Roi(x=10, y=10, width=40, height=40), threshold=200)


def test_rejects_roi_outside_image() -> None:
    image = np.zeros((100, 100, 3), dtype=np.uint8)

    with pytest.raises(ValueError, match="超出了图片范围"):
        build_mask(image, Roi(x=80, y=80, width=40, height=40))


def test_rejects_roi_that_is_too_small() -> None:
    image = np.zeros((100, 100, 3), dtype=np.uint8)

    with pytest.raises(ValueError, match="选区太小"):
        build_mask(image, Roi(x=10, y=10, width=2, height=20))


def test_decode_rejects_non_image_bytes() -> None:
    with pytest.raises(ValueError, match="无法读取图片"):
        decode_image(b"not an image")


def test_ai_mode_reports_missing_model(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.setenv("OMA_LAMA_MODEL", str(tmp_path / "missing.onnx"))
    clear_model_cache()
    try:
        with pytest.raises(AIModelUnavailableError, match="未找到 LaMa 模型"):
            remove_watermark(
                make_watermarked_image(),
                Roi(x=80, y=85, width=180, height=100),
                engine="ai",
            )
    finally:
        clear_model_cache()


@pytest.mark.skipif(not model_available(), reason="LaMa model is not downloaded")
def test_ai_mode_leaves_unmasked_pixels_unchanged() -> None:
    image = make_watermarked_image()
    roi = Roi(x=80, y=85, width=180, height=100)

    result = remove_watermark(image, roi, threshold=200, expand=4, engine="ai")

    assert result.engine == "ai"
    outside = result.mask == 0
    assert np.array_equal(result.image[outside], image[outside])
    assert np.any(result.image[result.mask > 0] != image[result.mask > 0])
