# PyInstaller spec for the watermark remover desktop app.
from pathlib import Path
import os
import sys

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

ROOT = Path(SPECPATH).resolve().parent
APP_NAME = "Watermark Remover"
VERSION = os.environ.get("OMA_APP_VERSION", "0.1.3")

datas = [
    (str(ROOT / "src" / "oma_watermark" / "static"), "oma_watermark/static"),
]
datas += collect_data_files("webview")

model = ROOT / "models" / "inpainting_lama_2025jan.onnx"
if model.is_file():
    datas.append((str(model), "models"))

hiddenimports = collect_submodules("uvicorn") + collect_submodules("webview")
hiddenimports += collect_submodules("python_multipart")
if sys.platform == "darwin":
    hiddenimports += ["webview.platforms.cocoa"]
elif sys.platform == "win32":
    hiddenimports += ["webview.platforms.edgechromium", "webview.platforms.winforms"]

icon = ROOT / "packaging" / ("icon.icns" if sys.platform == "darwin" else "icon.ico")
icon_path = str(icon) if icon.is_file() else None

a = Analysis(
    [str(ROOT / "packaging" / "desktop_entry.py")],
    pathex=[str(ROOT / "src")],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_path,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name=APP_NAME,
)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name=f"{APP_NAME}.app",
        icon=icon_path,
        bundle_identifier="com.wyf0931.oma-watermark",
        info_plist={
            "CFBundleDisplayName": "水印清除器",
            "CFBundleName": APP_NAME,
            "CFBundleShortVersionString": VERSION,
            "CFBundleVersion": "1",
            "LSMinimumSystemVersion": "12.0",
            "LSApplicationCategoryType": "public.app-category.photography",
            "NSHighResolutionCapable": True,
            "NSRequiresAquaSystemAppearance": False,
            "NSHumanReadableCopyright": "Copyright © 2026 Scott",
        },
    )
