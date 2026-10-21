# Watermark Remover

**English** | [简体中文](README.zh-CN.md)

[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-3776AB.svg)](https://www.python.org/)
[![Build desktop apps](https://github.com/wyf0931/oma-watermark/actions/workflows/build-desktop.yml/badge.svg)](https://github.com/wyf0931/oma-watermark/actions/workflows/build-desktop.yml)

Local web tool for removing light watermarks with OpenCV and optional LaMa AI inpainting.

Upload an image, draw a rectangle around the watermark, and the app detects light pixels inside the region and fills them in. Images are processed on your machine and never sent to a third-party service. The web UI and the macOS desktop app share the same FastAPI + HTML/CSS/JS interface.

![Watermark Remover on macOS after AI inpainting](docs/screenshot.png)

*macOS desktop mode. The native title bar is provided by macOS and is not part of the web UI.*

## Features

- **Local by design** — images stay in memory on your machine; no uploads, accounts, or history.
- **Two repair engines** — LaMa AI inpainting by default, with automatic fallback to fast OpenCV inpainting when the model is unavailable.
- **Manual, predictable ROI** — only the selected rectangle is modified; threshold and edge expansion are adjustable.
- **Web and desktop** — run in a browser, or use the native macOS app; an optional Windows ZIP build is available.
- **Result and mask preview** — compare the repaired image with the detected watermark area, then download it.

## Quick Start

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run oma-watermark
```

Open <http://127.0.0.1:8000>.

AI inpainting uses the [OpenCV LaMa ONNX model](https://huggingface.co/opencv/inpainting_lama) (~93 MB). Download it once:

```bash
uv run oma-watermark-download-model
```

Fast mode works without the model. If Hugging Face is unreachable, see [AI model setup](docs/install.md#ai-model-setup).

## Usage

1. Drop or choose an image (PNG, JPEG, WebP, BMP; max 25 MB).
2. Drag a rectangle around the watermark.
3. Keep **AI · LaMa** for textured backgrounds, or switch to **Fast · OpenCV** for simple ones. If the model is missing, the app falls back to Fast automatically.
4. Adjust **Threshold** and **Edge expand** if needed.
5. Run the repair, switch between **Result** and **Mask** views, then download the image.

**Threshold** — pixels whose B, G, and R channels are all above this value are treated as watermark. Lower it if traces remain; raise it if the background is being selected.

**Edge expand** — expands the mask to cover fringes, shadows, and anti-aliasing. Default is 6 px (range 0–12).

## Desktop App

Download `Watermark-Remover-*.dmg` from [GitHub Releases](https://github.com/wyf0931/oma-watermark/releases), open it, and drag the app into Applications. The DMG bundles the LaMa model, so AI mode works offline. Builds are ad-hoc signed and not notarized; on first launch you may need to right-click the app and choose **Open**.

For local desktop mode, packaging, Windows builds, and CI details, see [Desktop and packaging](docs/desktop.md).

## How It Works

1. The frontend sends the image, ROI, threshold, expansion, and mode to `POST /api/remove`.
2. The server selects light pixels inside the ROI with `cv2.inRange` and dilates the mask.
3. **Fast** uses `cv2.inpaint(..., cv2.INPAINT_TELEA)`; **AI** crops a square around the mask, runs LaMa at 512×512 via OpenCV DNN, and pastes back only masked pixels.
4. The API returns the result, a red mask overlay, and metadata.

See [Architecture](docs/architecture.md) for the full pipeline and code map.

## Documentation

| Guide | Contents |
| --- | --- |
| [Installation](docs/install.md) | Web setup, AI model download, proxy, desktop prerequisites |
| [Desktop and packaging](docs/desktop.md) | DMG/Windows builds, GitHub Actions, signing |
| [Architecture](docs/architecture.md) | Pipeline, invariants, project layout, UI theme |
| [API](docs/api.md) | `POST /api/remove`, `GET /api/health`, errors |
| [Development](docs/development.md) | Tests, lint, CSS build, contribution workflow |
| [FAQ and limitations](docs/faq.md) | Supported inputs, known limits, troubleshooting |

Chinese documentation: [README](README.zh-CN.md) · [docs/zh-CN](docs/zh-CN/).

## Project Layout

```text
src/oma_watermark/     FastAPI app, core algorithms, LaMa, desktop shell, web UI
packaging/             PyInstaller spec, icons, DMG/Windows build scripts
tests/                 Algorithm and API tests
docs/                  Detailed guides and screenshots
```

## Contributing

Issues and pull requests are welcome. For significant changes, open an issue first to discuss the approach. Before submitting, run the checks listed in [Development](docs/development.md#checks).

## License

[MIT](LICENSE) © 2026 Scott. The bundled LaMa model is licensed under Apache-2.0.
