# Installation

## Requirements

- Python 3.12 or newer
- [uv](https://docs.astral.sh/uv/)
- macOS 12+ for the desktop app (Web mode runs anywhere Python and OpenCV run)
- Node.js 20+ only when rebuilding the CSS

## Web

```bash
git clone https://github.com/wyf0931/oma-watermark.git
cd oma-watermark
uv sync
uv run oma-watermark
```

Open <http://127.0.0.1:8000>. The server binds to localhost by default.

Fast mode works immediately. AI mode additionally needs the LaMa model below.

## AI Model Setup

The optional model is the [OpenCV LaMa ONNX model](https://huggingface.co/opencv/inpainting_lama) (~93 MB, Apache-2.0). Download it once:

```bash
uv run oma-watermark-download-model
```

The file is stored at `models/inpainting_lama_2025jan.onnx`; `models/` is gitignored.

If Hugging Face is unreachable, configure a proxy first:

```bash
export https_proxy=http://127.0.0.1:7897
export http_proxy=http://127.0.0.1:7897
export all_proxy=socks5://127.0.0.1:7897
uv run oma-watermark-download-model
```

Alternatively use the Hugging Face CLI directly:

```bash
uv run hf download opencv/inpainting_lama inpainting_lama_2025jan.onnx --local-dir models
```

To use a model stored elsewhere:

```bash
OMA_LAMA_MODEL=/path/to/inpainting_lama_2025jan.onnx uv run oma-watermark
```

The Windows build expects the model in the packaged application directory. The build scripts download it automatically.

## Desktop Prerequisites

The macOS desktop app uses [pywebview](https://pywebview.flowrl.com/) with WKWebView. Install the desktop extra:

```bash
uv sync --extra desktop
uv run oma-watermark-desktop
```

Building from source also requires `npm ci && npm run build:css`. See [Desktop and packaging](./desktop.md).

## Troubleshooting

- **AI mode falls back to Fast** — the model is missing or unreadable. Run the download command and check `/api/health`.
- **First AI request is slow** — the model loads lazily (~8 s on first use, then roughly 3–4 s per image on CPU).
- **`hf` command not found** — run it through `uv run hf`, or re-run `uv sync`.
- **Port already in use** — stop the other process, or start the app again; the desktop shell picks a random free port automatically.
