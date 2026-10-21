# Desktop and Packaging

The desktop app is a [pywebview](https://pywebview.flowrl.com/) window backed by the same local FastAPI server. On macOS it uses WKWebView and a native title bar; on Windows it uses WebView2. No page is loaded from the network.

## Install a Release

Download `Watermark-Remover-<version>-<arch>.dmg` from [GitHub Releases](https://github.com/wyf0931/oma-watermark/releases), open it, and drag the app into Applications.

- The DMG bundles the LaMa model, so AI mode works offline.
- Builds are **ad-hoc signed and not notarized**. On first launch macOS may block the app; right-click it and choose **Open**, or run:

```bash
xattr -dr com.apple.quarantine "/Applications/Watermark Remover.app"
```

Distribution to the general public requires an Apple Developer ID certificate and notarization.

## Run Locally

```bash
npm ci
npm run build:css
uv sync --extra desktop
uv run oma-watermark-desktop
```

The desktop window is 1240×880 by default with a minimum of about 980×780. It hides the website header (`?desktop=1`), uses the native title bar, hides the page scrollbar, and keeps usage help in the toolbar **?** dialog.

## Build a DMG

```bash
bash packaging/build_macos.sh
```

The script:

1. checks for and downloads the LaMa model;
2. builds the local Tailwind/daisyUI CSS;
3. produces `Watermark Remover.app` with PyInstaller;
4. applies an ad-hoc signature;
5. creates `dist/Watermark-Remover-<version>-<arch>.dmg` with an Applications shortcut.

Set the version with `OMA_APP_VERSION`:

```bash
OMA_APP_VERSION=0.2.0 bash packaging/build_macos.sh
```

## Build for Windows

```powershell
npm ci
npm run build:css
uv sync --extra desktop
powershell -ExecutionPolicy Bypass -File packaging/build_windows.ps1
```

The artifact is `dist/Watermark-Remover-<version>-windows.zip`. It is a ZIP, not an installer, and relies on the Microsoft Edge WebView2 Runtime (preinstalled on most Windows 10/11 systems).

## GitHub Actions

[`.github/workflows/build-desktop.yml`](../.github/workflows/build-desktop.yml) runs on manual dispatch and on `v*` tags:

- `macos-14` (Apple Silicon arm64) builds the DMG;
- `windows-latest` builds the ZIP and is allowed to fail without blocking macOS;
- the LaMa model is cached between runs;
- tag builds create a GitHub Release with the artifacts.

## Packaging Notes

- The PyInstaller entry point is `packaging/desktop_entry.py`; the spec is `packaging/oma-watermark.spec`.
- New static files or model resources must be added to the spec's `datas`.
- Frozen resource paths are resolved by `_static_dir()` in `app.py` and `_default_model_path()` in `lama.py` using `sys._MEIPASS`.
- Downloads work only because `desktop.py` sets `webview.settings["ALLOW_DOWNLOADS"] = True`.
- The app is macOS-arm64 by default; adjust the runner and target architecture for Intel builds.
