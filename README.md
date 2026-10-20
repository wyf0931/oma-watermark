# 水印清除器（MVP）

一个本地运行的 Web 小工具：上传图片，用鼠标框出水印所在区域，自动识别浅色水印像素，再选择快速 OpenCV 修复或可选的 LaMa AI 精修。

不依赖桌面 GUI，macOS / Linux 都能跑；图片只发送到本机 FastAPI 服务。

![水印清除器界面：AI 精修后的图片结果](docs/screenshot.png)

## 快速开始

需要 Python 3.12+ 和 [uv](https://docs.astral.sh/uv/)。

```bash
uv sync
uv run oma-watermark
```

打开 <http://127.0.0.1:8000>。

### 可选：安装 AI 精修模型

快速模式不需要模型。AI 模式使用 [OpenCV 官方 LaMa ONNX 模型](https://huggingface.co/opencv/inpainting_lama)（约 93 MB），只需下载一次：

```bash
uv run oma-watermark-download-model
```

下载命令使用项目依赖中的 Hugging Face CLI（`uv sync` 已安装）。如果 Hugging Face 无法访问，先设置代理再运行下载命令：

```bash
export https_proxy=http://127.0.0.1:7897
export http_proxy=http://127.0.0.1:7897
export all_proxy=socks5://127.0.0.1:7897
uv run oma-watermark-download-model
```

也可以直接用 `hf`：

```bash
uv run hf download opencv/inpainting_lama inpainting_lama_2025jan.onnx --local-dir models
```

默认模型路径是 `models/inpainting_lama_2025jan.onnx`。如需放到别处：

```bash
OMA_LAMA_MODEL=/path/to/inpainting_lama_2025jan.onnx uv run oma-watermark
```

模型文件不提交到仓库，`models/` 已加入 `.gitignore`。模型采用 Apache-2.0 许可。

## 使用步骤

1. 拖入或选择一张图片（PNG / JPEG / WebP / BMP，≤ 25 MB）。
2. 在原图上拖动鼠标，框出一个包含水印的矩形。
3. 选择修复模式：
   - **快速 · OpenCV**：无需模型，约 0.1 秒，适合纯色/简单背景；修复区域偏平滑。
   - **AI 精修 · LaMa**：需要模型，CPU 推理约 3–4 秒（首次加载模型约 8 秒），更擅长恢复纹理、鞋履、地面、衣物等复杂背景。
4. 按需调整「亮度阈值」和「边缘扩展」。
5. 点击「祛除水印」，在「原图 / 结果 / 检测区」之间切换检查，满意后下载。

### 参数说明

- **亮度阈值**：B/G/R 三个通道都高于该值的像素会被当作水印。水印没清干净就调低，误选背景就调高。
- **边缘扩展**：mask 向外扩展的像素数。调大能覆盖白边、阴影和抗锯齿，但修复区域更大；调小更清晰，但可能残留水印边缘。默认 6px。

## 实现方式

1. 浏览器把原图、ROI、阈值、扩展值和修复模式发送到 `POST /api/remove`。
2. 服务端在 ROI 内用 `cv2.inRange` 选中所有通道亮度都高于阈值的像素。
3. 按「边缘扩展」对 mask 做形态学膨胀。
4. 根据模式修复：
   - **快速**：`cv2.inpaint(..., cv2.INPAINT_TELEA)`。
   - **AI**：裁出 mask 周围的正方形区域，缩放至 512×512，通过 OpenCV DNN 跑 LaMa，再把 mask 内的像素贴回原图。
5. 返回结果图、红色检测区预览和修复像素数。

核心代码在 [`src/oma_watermark/core.py`](src/oma_watermark/core.py) 和 [`src/oma_watermark/lama.py`](src/oma_watermark/lama.py)，Web UI 在 [`src/oma_watermark/static/`](src/oma_watermark/static/)。

## 测试

```bash
uv run pytest
```

测试覆盖 ROI 校验、mask 生成、边缘扩展、修复范围、API 成功与错误路径，以及 AI 模式缺少模型时的错误处理。下载模型后，本地测试还会运行一次 LaMa 冒烟测试；没有模型时该测试自动跳过。

## MVP 边界

- 只处理**浅色/白色**水印；深色水印需要另做检测策略。
- 单张图片、单个矩形选区；没有自动检测、批量处理或画笔 mask。
- 快速模式是扩散式内容填充，修复区域会变平滑，复杂纹理上尤其明显。
- AI 模式受 512×512 模型输入限制；大选区会被缩放，结果可能更柔和，也可能会“脑补”背景。
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
| `expand` | int | 边缘扩展像素，0–12，默认 6 |
| `mode` | string | `fast`（默认）或 `ai` |

返回 JSON：`result`、`mask_overlay`（data URL）、`filename`、尺寸、`detected_pixels`、`mode`、`expand`、`roi`。

`GET /api/health` 返回 `status`、`ai_available` 和 `ai_engine`，用于前端显示模型是否就绪。
