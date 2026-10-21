# Architecture

## Data Flow

```text
Browser / pywebview
        │  GET /api/health
        │  POST /api/remove (image + ROI + options)
        ▼
FastAPI (app.py)
  ├─ validate upload size (25 MB) and mode
  ├─ core.decode_image() — applies EXIF orientation
  ├─ core.remove_watermark(engine=...)
  │    ├─ fast → cv2.inpaint (TELEA)
  │    └─ ai   → lama.inpaint_with_lama()
  └─ result + mask_overlay data URLs + metadata
```

## Repair Pipeline

1. Validate the ROI against the decoded image bounds.
2. Inside the ROI, select pixels whose blue, green, and red channels are all above the threshold with `cv2.inRange`.
3. Dilate the mask by the requested `expand` amount (0–12 px).
4. Repair the masked area:
   - **Fast** — `cv2.inpaint(..., cv2.INPAINT_TELEA)`, no model required.
   - **AI** — crop a square around the mask, resize to 512×512, run the LaMa ONNX model through `cv2.dnn`, resize back, and paste only masked pixels into the original image.
5. Encode the result and a red mask overlay as data URLs.

The AI model loads lazily on first use. Model loading and `cv2.dnn` inference are protected by a lock, so requests are serialized.

## Invariants

1. ROI coordinates are original-image pixel coordinates, never CSS pixels.
2. The mask is clipped to the ROI; pixels outside it must remain unchanged.
3. The server applies EXIF orientation so preview and ROI coordinates agree.
4. Only light/white pixels are detected; all B/G/R channels must exceed the threshold.
5. The AI model is optional. Missing models return `503`, and the UI falls back to Fast.
6. AI mode pastes back masked pixels only.
7. Images are processed in memory; nothing is written to disk or logged.

## Project Layout

```text
src/oma_watermark/
  __init__.py          `oma-watermark` web entry point
  app.py               FastAPI routes, upload limits, static files, health
  core.py              decoding, mask generation, fast inpainting, encoding
  lama.py              model discovery, lazy loading, cropped inference
  desktop.py           pywebview window, local server lifecycle, downloads
  download_model.py    model download CLI
  static/              HTML, CSS, JS, generated Tailwind CSS
packaging/
  desktop_entry.py     PyInstaller entry point
  oma-watermark.spec   PyInstaller spec
  build_macos.sh       DMG build
  build_windows.ps1    Windows ZIP build
tests/                 core and API tests
```

## UI and Theme

- The interface follows the Apple design language documented in [`DESIGN.md`](../DESIGN.md).
- daisyUI themes `apple` and `apple-dark` are defined in `static/app.css` via `@plugin "daisyui/theme"` and follow the system color scheme.
- Tailwind and daisyUI are built locally into `static/app.built.css`; there is no CDN dependency.
- `?desktop=1` switches to desktop mode: native title bar, compact toolbar, no page scrollbar.

## Known Limits

See [FAQ and limitations](./faq.md) for supported inputs, model limits, and packaging caveats.
