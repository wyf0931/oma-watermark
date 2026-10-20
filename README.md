# 水印清除器（MVP）

一个本地运行的 Web 小工具：上传图片，用鼠标框出水印所在区域，自动识别区域内的浅色水印并用 OpenCV 修复。

不依赖桌面 GUI，macOS / Linux 都能跑；图片只发送到本机 FastAPI 服务。

![水印清除器界面：框选水印并查看检测区](docs/screenshot.png)

## 快速开始

需要 Python 3.12+ 和 [uv](https://docs.astral.sh/uv/)。

```bash
uv sync
uv run oma-watermark
```

打开 <http://127.0.0.1:8000>。

### 使用步骤

1. 拖入或选择一张图片（PNG / JPEG / WebP / BMP，≤ 25 MB）。
2. 在原图上拖动鼠标，框出一个包含水印的矩形。
3. 点击「祛除水印」。
4. 在「原图 / 结果 / 检测区」之间切换检查效果，满意后下载。

如果水印没清干净，先调低「亮度阈值」再处理；如果误伤了背景，调高阈值或把选区收得更紧。

## 实现方式

1. 浏览器把原图、ROI 矩形和亮度阈值发送到 `POST /api/remove`。
2. 服务端在 ROI 内用 `cv2.inRange` 选中所有通道亮度都高于阈值的像素。
3. 对 mask 做 6 像素膨胀，覆盖抗锯齿边缘和轻微文字阴影。
4. 用 `cv2.inpaint(..., cv2.INPAINT_TELEA)` 修复，返回结果图和红色检测区预览。

核心代码在 [`src/oma_watermark/core.py`](src/oma_watermark/core.py)，Web UI 在 [`src/oma_watermark/static/`](src/oma_watermark/static/)。

## 测试

```bash
uv run pytest
```

测试覆盖 ROI 校验、mask 生成、修复范围、API 成功与错误路径。

## MVP 边界

- 只处理**浅色/白色**水印；深色水印需要另做检测策略。
- 单张图片、单个矩形选区；没有自动检测、批量处理或画笔 mask。
- 修复是内容填充，不是生成式重绘；复杂纹理上可能有涂抹感。
- 透明 PNG 会先合成到白底，输出不保留 alpha。
- 页面样式使用 daisyUI CDN，首次打开需要联网；图片处理本身不联网。
- 图片在内存中处理，不落盘、不保存历史。

## API

`POST /api/remove`（multipart/form-data）

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `file` | file | 原图 |
| `x`, `y` | int | ROI 左上角 |
| `width`, `height` | int | ROI 尺寸 |
| `threshold` | int | 亮度阈值，默认 200 |

返回 JSON：`result`、`mask_overlay`（data URL）、`filename`、尺寸、`detected_pixels`、`roi`。
