# Development

## Setup

```bash
uv sync                       # web and test dependencies
uv sync --extra desktop       # optional desktop dependencies
npm ci                        # CSS build dependencies
```

Run the app:

```bash
uv run oma-watermark
uv run oma-watermark-desktop
```

## Tests

```bash
uv run pytest
```

Coverage includes ROI validation, mask generation, edge expansion, repair bounds, API success and error paths, and missing-model handling. When the LaMa model is present, a smoke test runs; otherwise it is skipped.

## CSS

Edit `src/oma_watermark/static/app.css`, `index.html`, or `style.css`, then rebuild:

```bash
npm run build:css
```

Never edit `app.built.css` by hand. The generated file is committed so the app works offline and in packaged builds.

## Checks

Run these before committing:

```bash
npm run build:css
ruff check src tests
ruff format --check src tests
uv lock --check
uv run pytest
node --check src/oma_watermark/static/app.js
```

## Contribution Workflow

1. Open an issue for significant behavior or API changes.
2. Add or update tests first for algorithm and API changes.
3. Keep ROI coordinates in original-image pixels and masks clipped to the ROI.
4. Update the relevant docs when behavior, parameters, or packaging changes:
   - `README.md` and `README.zh-CN.md` for user-facing behavior
   - `docs/` and `docs/zh-CN/` for detailed guides
   - `AGENTS.md` for architecture invariants and maintenance rules
5. Submit a pull request with a short description and test evidence.

## Static Files and Packaging

New static assets or model files must be added to `packaging/oma-watermark.spec`. Verify a packaged build after changing paths, the spec, or build scripts. See [Desktop and packaging](./desktop.md).

## Manual Verification

- Web: upload → select ROI → Fast and AI → result/mask → download.
- Desktop: `uv run oma-watermark-desktop`; confirm the website header is hidden, the native title bar is used, and downloads work.
- Theme: check light and dark modes after rebuilding CSS.
