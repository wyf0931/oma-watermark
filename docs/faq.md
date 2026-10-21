# FAQ and Limitations

## Supported Inputs

- Image formats: PNG, JPEG, WebP, BMP
- Maximum upload: 25 MB
- One image at a time, one rectangular ROI per image
- Watermarks must be light or white

## Known Limitations

- **Light watermarks only.** Detection requires all B/G/R channels to be bright. Dark or colored watermarks need a different strategy.
- **No automatic detection.** You must draw the rectangle manually.
- **No batch processing, brush mask, accounts, or history.** This is intentionally an MVP.
- **Fast mode smooths textures.** TELEA diffusion works well on simple backgrounds and blurs complex ones.
- **AI input is 512×512.** Large ROIs are resized, so details may soften and the model may hallucinate background.
- **Transparent PNGs lose alpha.** They are composited onto white before processing.
- **AI is CPU-only.** Expect about 8 seconds for the first model load and 3–4 seconds per image on an M4 Pro.
- **macOS builds are ad-hoc signed and not notarized.** First launch may require right-click → Open.
- **Windows builds are ZIPs relying on WebView2**, not installers.
- **No network access at runtime.** Only the one-time model download uses the network.

## Troubleshooting

### AI mode is unavailable or falls back to Fast

Check `/api/health`. If `ai_available` is false, download the model:

```bash
uv run oma-watermark-download-model
```

Then verify `models/inpainting_lama_2025jan.onnx` exists, or set `OMA_LAMA_MODEL` to its path.

### Hugging Face download fails

Set a proxy before running the download command:

```bash
export https_proxy=http://127.0.0.1:7897
export http_proxy=http://127.0.0.1:7897
export all_proxy=socks5://127.0.0.1:7897
```

### The wrong area is repaired

- Confirm the ROI is drawn on the image, not the page margin.
- Lower **Threshold** if watermark pixels remain.
- Raise **Threshold** if background is being removed.
- Increase **Edge expand** for fringes, shadows, or anti-aliasing.

### The app looks unstyled or the layout is broken

Rebuild the CSS and restart:

```bash
npm run build:css
```

### The macOS app cannot be opened

Right-click the app and choose **Open**, or remove the quarantine attribute:

```bash
xattr -dr com.apple.quarantine "/Applications/Watermark Remover.app"
```

### Downloads do nothing in the desktop app

Desktop downloads require `webview.settings["ALLOW_DOWNLOADS"] = True`. This is set in `desktop.py`; confirm you are running the current build.
