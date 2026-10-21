# 架构

## 数据流

```text
浏览器 / pywebview
        │  GET /api/health
        │  POST /api/remove（图片 + ROI + 参数）
        ▼
FastAPI (app.py)
  ├─ 校验上传大小（25 MB）和模式
  ├─ core.decode_image() — 处理 EXIF 方向
  ├─ core.remove_watermark(engine=...)
  │    ├─ fast → cv2.inpaint (TELEA)
  │    └─ ai   → lama.inpaint_with_lama()
  └─ 结果图 + mask_overlay data URL + 元数据
```

## 修复流程

1. 用解码后的图片尺寸校验 ROI。
2. 在 ROI 内用 `cv2.inRange` 选中 B、G、R 三个通道都高于阈值的像素。
3. 按 `expand` 对 mask 做膨胀（0–12 px）。
4. 修复选区：
   - **快速** — `cv2.inpaint(..., cv2.INPAINT_TELEA)`，无需模型。
   - **AI** — 裁出 mask 周围的正方形区域，缩放至 512×512，通过 `cv2.dnn` 运行 LaMa ONNX 模型，再缩放回来，只把 mask 内像素贴回原图。
5. 将结果和红色检测区预览编码为 data URL。

AI 模型首次使用时懒加载。模型加载和 `cv2.dnn` 推理由锁保护，因此请求串行执行。

## 关键不变量

1. ROI 坐标始终是原图像素坐标，不是 CSS 像素。
2. mask 必须裁剪到 ROI 内，ROI 外像素不得改变。
3. 服务端负责 EXIF 方向，保证预览和 ROI 坐标一致。
4. 只检测浅色/白色像素，B/G/R 三个通道都必须高于阈值。
5. AI 模型是可选资源。模型缺失返回 `503`，前端回退到快速模式。
6. AI 模式只贴回 mask 内像素。
7. 图片在内存中处理，不落盘、不记录上传内容。

## 项目结构

```text
src/oma_watermark/
  __init__.py          `oma-watermark` Web 入口
  app.py               FastAPI 路由、上传限制、静态资源、健康检查
  core.py              解码、mask、快速修复、编码
  lama.py              模型定位、懒加载、裁剪推理
  desktop.py           pywebview 窗口、服务生命周期、下载开关
  download_model.py    模型下载 CLI
  static/              HTML、CSS、JS、生成的 Tailwind CSS
packaging/
  desktop_entry.py     PyInstaller 入口
  oma-watermark.spec   PyInstaller spec
  build_macos.sh       DMG 构建
  build_windows.ps1    Windows ZIP 构建
tests/                 核心算法与 API 测试
```

## UI 与主题

- 界面遵循 [`DESIGN.md`](../../DESIGN.md) 中的 Apple 设计语言。
- daisyUI 的 `apple` 和 `apple-dark` 主题在 `static/app.css` 中通过 `@plugin "daisyui/theme"` 定义，跟随系统浅色/深色模式。
- Tailwind 和 daisyUI 在本地构建到 `static/app.built.css`，不依赖 CDN。
- `?desktop=1` 切换到桌面模式：原生标题栏、紧凑工具栏、无页面滚动条。

## 已知边界

支持的输入、模型限制和打包注意事项见 [FAQ 与边界](./faq.md)。
