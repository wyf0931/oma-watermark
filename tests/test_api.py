import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from oma_watermark.app import app
from oma_watermark.lama import clear_model_cache, model_available

client = TestClient(app)


def make_png() -> bytes:
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
    ok, buffer = cv2.imencode(".png", image)
    assert ok
    return buffer.tobytes()


def test_index_and_static_assets_are_served() -> None:
    assert client.get("/").status_code == 200
    assert client.get("/static/app.js").status_code == 200
    assert client.get("/static/style.css").status_code == 200


def test_remove_endpoint_returns_images_and_stats() -> None:
    response = client.post(
        "/api/remove",
        files={"file": ("sample.png", make_png(), "image/png")},
        data={
            "x": "80",
            "y": "85",
            "width": "180",
            "height": "100",
            "threshold": "200",
        },
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["result"].startswith("data:image/png;base64,")
    assert payload["mask_overlay"].startswith("data:image/png;base64,")
    assert payload["detected_pixels"] > 0
    assert payload["filename"] == "cleaned_sample.png"
    assert payload["width"] == 320
    assert payload["height"] == 240
    assert payload["mode"] == "fast"
    assert payload["expand"] == 6


def test_remove_endpoint_rejects_roi_outside_image() -> None:
    response = client.post(
        "/api/remove",
        files={"file": ("sample.png", make_png(), "image/png")},
        data={
            "x": "300",
            "y": "220",
            "width": "100",
            "height": "100",
            "threshold": "200",
        },
    )

    assert response.status_code == 422
    assert "超出" in response.json()["detail"]


def test_remove_endpoint_rejects_non_image() -> None:
    response = client.post(
        "/api/remove",
        files={"file": ("notes.txt", b"hello", "text/plain")},
        data={"x": "0", "y": "0", "width": "10", "height": "10"},
    )

    assert response.status_code == 422
    assert "无法读取图片" in response.json()["detail"]


def test_remove_endpoint_rejects_invalid_mode() -> None:
    response = client.post(
        "/api/remove",
        files={"file": ("sample.png", make_png(), "image/png")},
        data={
            "x": "80",
            "y": "85",
            "width": "180",
            "height": "100",
            "mode": "unknown",
        },
    )

    assert response.status_code == 422
    assert "fast 或 ai" in response.json()["detail"]


def test_remove_endpoint_rejects_out_of_range_expand() -> None:
    response = client.post(
        "/api/remove",
        files={"file": ("sample.png", make_png(), "image/png")},
        data={
            "x": "80",
            "y": "85",
            "width": "180",
            "height": "100",
            "expand": "13",
        },
    )

    assert response.status_code == 422
    assert "边缘扩展" in response.json()["detail"]


def test_ai_mode_reports_missing_model(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("OMA_LAMA_MODEL", str(tmp_path / "missing.onnx"))
    clear_model_cache()
    try:
        response = client.post(
            "/api/remove",
            files={"file": ("sample.png", make_png(), "image/png")},
            data={
                "x": "80",
                "y": "85",
                "width": "180",
                "height": "100",
                "mode": "ai",
            },
        )
    finally:
        clear_model_cache()

    assert response.status_code == 503
    assert "oma-watermark-download-model" in response.json()["detail"]


@pytest.mark.skipif(not model_available(), reason="LaMa model is not downloaded")
def test_ai_mode_endpoint_succeeds() -> None:
    clear_model_cache()
    response = client.post(
        "/api/remove",
        files={"file": ("sample.png", make_png(), "image/png")},
        data={
            "x": "80",
            "y": "85",
            "width": "180",
            "height": "100",
            "threshold": "200",
            "expand": "4",
            "mode": "ai",
        },
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["mode"] == "ai"
    assert payload["expand"] == 4
    assert payload["detected_pixels"] > 0
    assert payload["result"].startswith("data:image/png;base64,")


def test_health_endpoint() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert isinstance(payload["ai_available"], bool)
    assert "LaMa" in payload["ai_engine"]
