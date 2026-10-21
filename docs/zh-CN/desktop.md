# 桌面与打包

桌面版是一个 [pywebview](https://pywebview.flowrl.com/) 窗口，后端仍是同一个本机 FastAPI 服务。macOS 使用 WKWebView 和原生标题栏，Windows 使用 WebView2。界面不加载任何网络资源。

## 安装发布版

从 [GitHub Releases](https://github.com/wyf0931/oma-watermark/releases) 下载 `Watermark-Remover-<version>-<arch>.dmg`，打开后把应用拖入 Applications。

- DMG 内置 LaMa 模型，AI 模式可离线使用。
- 构建为 **ad-hoc 签名、未公证**。首次打开可能被 macOS 拦截；右键应用选择「打开」，或执行：

```bash
xattr -dr com.apple.quarantine "/Applications/Watermark Remover.app"
```

面向公众分发需要 Apple Developer ID 证书和 notarization。

## 本地运行

```bash
npm ci
npm run build:css
uv sync --extra desktop
uv run oma-watermark-desktop
```

桌面窗口默认 1240×880，最小约 980×780。通过 `?desktop=1` 隐藏网站顶部导航，使用原生标题栏，隐藏页面滚动条，并把使用说明放在工具栏的 **?** 弹窗中。

## 构建 DMG

```bash
bash packaging/build_macos.sh
```

脚本会：

1. 检查并下载 LaMa 模型；
2. 构建本地 Tailwind/daisyUI CSS；
3. 用 PyInstaller 生成 `Watermark Remover.app`；
4. 执行 ad-hoc 签名；
5. 生成带 Applications 快捷方式的 `dist/Watermark-Remover-<version>-<arch>.dmg`。

用 `OMA_APP_VERSION` 指定版本：

```bash
OMA_APP_VERSION=0.2.0 bash packaging/build_macos.sh
```

## 构建 Windows 版

```powershell
npm ci
npm run build:css
uv sync --extra desktop
powershell -ExecutionPolicy Bypass -File packaging/build_windows.ps1
```

产物为 `dist/Watermark-Remover-<version>-windows.zip`。它是 ZIP 而非安装器，依赖 Microsoft Edge WebView2 Runtime（Windows 10/11 通常已预装）。

## GitHub Actions

[`.github/workflows/build-desktop.yml`](../../.github/workflows/build-desktop.yml) 支持手动触发和推送 `v*` tag：

- `macos-14`（Apple Silicon arm64）生成 DMG；
- `windows-latest` 生成 ZIP，失败不阻塞 macOS 构建；
- LaMa 模型在构建之间缓存；
- tag 构建会创建 GitHub Release 并附带产物。

## 打包注意事项

- PyInstaller 入口是 `packaging/desktop_entry.py`，spec 是 `packaging/oma-watermark.spec`。
- 新增静态文件或模型资源时，必须加入 spec 的 `datas`。
- 冻结后的资源路径由 `app.py` 的 `_static_dir()` 和 `lama.py` 的 `_default_model_path()` 通过 `sys._MEIPASS` 解析。
- 桌面下载可用是因为 `desktop.py` 设置了 `webview.settings["ALLOW_DOWNLOADS"] = True`。
- 默认构建 macOS arm64；Intel 构建需要调整 runner 和目标架构。
