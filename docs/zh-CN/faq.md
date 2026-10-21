# FAQ 与边界

## 支持的输入

- 图片格式：PNG、JPEG、WebP、BMP
- 最大上传：25 MB
- 一次一张图片，一张图片一个矩形选区
- 水印必须是浅色或白色

## 已知限制

- **只支持浅色水印。** 检测要求 B/G/R 三个通道都足够亮；深色或彩色水印需要另行设计策略。
- **没有自动检测。** 必须手动框选矩形。
- **没有批量处理、画笔 mask、账号或历史记录。** 项目有意保持 MVP。
- **快速模式会平滑纹理。** TELEA 扩散适合简单背景，复杂纹理会变模糊。
- **AI 输入固定 512×512。** 大选区会被缩放，细节可能变柔和，也可能“脑补”背景。
- **透明 PNG 会丢失 alpha。** 处理前会合成到白底。
- **AI 仅使用 CPU。** M4 Pro 上首次加载约 8 秒，之后每张约 3–4 秒。
- **macOS 构建为 ad-hoc 签名、未公证。** 首次打开可能需要右键 →「打开」。
- **Windows 构建是依赖 WebView2 的 ZIP**，不是安装器。
- **运行时不联网。** 只有首次下载模型需要网络。

## 故障排查

### AI 模式不可用或回退到快速模式

检查 `/api/health`。如果 `ai_available` 为 false，下载模型：

```bash
uv run oma-watermark-download-model
```

确认 `models/inpainting_lama_2025jan.onnx` 存在，或用 `OMA_LAMA_MODEL` 指向模型路径。

### Hugging Face 下载失败

下载前设置代理：

```bash
export https_proxy=http://127.0.0.1:7897
export http_proxy=http://127.0.0.1:7897
export all_proxy=socks5://127.0.0.1:7897
```

### 修复了错误区域

- 确认矩形画在图片上，而不是页面空白处。
- 残留水印边缘时调低 **亮度阈值**。
- 背景被误选时调高 **亮度阈值**。
- 白边、阴影或抗锯齿残留时调大 **边缘扩展**。

### 界面样式丢失或布局错乱

重新构建 CSS 并重启：

```bash
npm run build:css
```

### macOS 应用无法打开

右键应用选择「打开」，或移除隔离属性：

```bash
xattr -dr com.apple.quarantine "/Applications/Watermark Remover.app"
```

### 桌面版点击下载无反应

桌面下载依赖 `webview.settings["ALLOW_DOWNLOADS"] = True`，该设置位于 `desktop.py`。请确认运行的是最新构建。
