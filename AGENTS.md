# AGENTS.md

本文件面向在本仓库工作的编码 Agent（以及人类维护者），用于快速理解项目边界、关键链路和提交前检查。修改代码前先读本文件与 `README.md`。

## 项目目标

一个本地运行的 Web 水印清除工具：

1. 用户在浏览器上传图片。
2. 用户手工框选包含水印的矩形 ROI。
3. 服务端用 OpenCV 识别 ROI 内的浅色/白色像素并生成 mask。
4. 用户在两种修复引擎中选择：
   - `fast`：默认，`cv2.inpaint`，无需模型，速度快但修复区域偏平滑。
   - `ai`：可选，OpenCV DNN + LaMa ONNX，更擅长恢复纹理，需要单独下载约 93 MB 模型。
5. 前端展示原图、结果和检测区，并支持下载。

产品原则是 **MVP + YAGNI**：优先保持单图片、单矩形、无账号、无数据库、无持久化。AI 模式是可选增强，不要让未下载模型的环境无法使用快速模式。

## 技术栈

- Python 3.12+，`uv` 管理环境和锁文件
- FastAPI + Uvicorn
- OpenCV（`opencv-python-headless`）+ NumPy
- Pillow（EXIF 方向和透明通道处理）
- LaMa ONNX 通过 `cv2.dnn` 运行，无 PyTorch / ONNX Runtime 依赖
- 原生 HTML/CSS/JS，无前端构建步骤
- daisyUI 5 + Tailwind CSS 4 浏览器版（CDN）
- pytest + FastAPI TestClient

## 仓库结构

```text
docs/screenshot.png              README 展示图
src/oma_watermark/__init__.py    `oma-watermark` 入口，启动 Uvicorn
src/oma_watermark/app.py         FastAPI 路由、上传限制、静态文件、健康检查
src/oma_watermark/core.py        解码、mask、快速修复、编码与数据模型
src/oma_watermark/lama.py        LaMa 模型定位、懒加载、裁剪推理与错误类型
src/oma_watermark/download_model.py  `oma-watermark-download-model` 下载命令
src/oma_watermark/static/        Web UI（HTML / CSS / JS）
tests/test_core.py               算法、mask、AI 缺失/冒烟测试
tests/test_api.py                API 合约与错误路径测试
pyproject.toml                   依赖、脚本、pytest 配置
uv.lock                          锁文件，修改依赖后必须更新
models/                          本地下载的模型，已 gitignore，不提交
```

## 开发命令

```bash
uv sync                              # 安装依赖
uv run oma-watermark                 # 启动 http://127.0.0.1:8000
uv run oma-watermark-download-model  # 下载可选 LaMa 模型
uv run pytest                        # 运行测试
uv lock --check                      # 检查锁文件
node --check src/oma_watermark/static/app.js
ruff check src tests                 # 如本机有 ruff
ruff format --check src tests
uv build --wheel                     # 可选：确认静态资源被包含进 wheel
```

下载模型使用项目依赖中的 `hf` CLI（`huggingface-hub`）。若 Hugging Face 无法访问：

```bash
export https_proxy=http://127.0.0.1:7897
export http_proxy=http://127.0.0.1:7897
export all_proxy=socks5://127.0.0.1:7897
uv run oma-watermark-download-model
```

提交前至少运行：

```bash
uv lock --check
uv run pytest
node --check src/oma_watermark/static/app.js
```

需要视觉验证时，启动服务后在浏览器走完：上传 → 框选 → 快速/切换 AI → 处理 → 切换结果/检测区 → 下载。

## 架构与数据流

```text
Browser
  ├─ 读取图片为 object URL，仅用于预览
  ├─ 在 image 上拖拽，把显示坐标换算成原图像素 ROI
  ├─ GET /api/health 获取 ai_available
  └─ POST /api/remove
       multipart: file, x, y, width, height, threshold, expand, mode
        ↓
FastAPI app.py
  ├─ 限制上传大小 25 MB，校验 mode
  ├─ 调用 core.decode_image()，处理 EXIF 方向
  ├─ 调用 core.remove_watermark(..., engine=mode)
  └─ 返回 result / mask_overlay 的 data URL + 元数据
        ↓
core.py
  ├─ ROI 内 cv2.inRange(min(B,G,R) >= threshold)
  ├─ 按 expand 做椭圆核膨胀
  ├─ 全图 mask 只在 ROI 内置位
  ├─ fast: cv2.inpaint(..., INPAINT_TELEA)
  └─ ai:   lama.inpaint_with_lama(image, mask)
                ├─ mask 外接框扩展 15% 后取正方形 crop
                ├─ 缩放至 512×512
                ├─ cv2.dnn 懒加载 LaMa ONNX
                └─ 只把 mask 内像素贴回原图
```

### 关键不变量

1. **ROI 坐标始终是原图像素坐标**，不是浏览器显示坐标或 CSS 像素。
   - 前端换算在 `static/app.js` 的 `pointInImage()` / `rectFromPoints()`。
   - 图片缩放后 ROI 用百分比重新渲染。
2. **mask 必须限制在 ROI 内**。ROI 外的像素不得被修改。`tests/test_core.py` 已覆盖。
3. **服务端负责 EXIF 方向**。浏览器预览与服务端解码结果必须使用同一视觉方向，否则 ROI 会错位。
4. **边缘扩展 `expand` 的合法范围是 0–12，默认 6**。它用于覆盖抗锯齿、白边和常见文字阴影；调低容易留下水印轮廓，调高会扩大修复面积。
5. **只检测浅色/白色水印**。`cv2.inRange` 要求 B/G/R 三个通道都高于阈值。深色水印不属于当前范围。
6. **AI 模型是可选资源**。模型文件默认在 `models/inpainting_lama_2025jan.onnx`，可用 `OMA_LAMA_MODEL` 覆盖。模型不提交，`models/` 已 gitignore。
7. **AI 模型懒加载并串行推理**。`lama.py` 用锁保证多线程请求下模型只加载一次，且 `cv2.dnn` 推理不并发执行。
8. **AI 只贴回 mask 内像素**。mask 外必须保持原图，测试已覆盖。
9. **快速模式必须是默认模式**。模型缺失时页面仍可完整使用 OpenCV 修复。
10. **图片在内存中处理**，不落盘、不保存历史、不记录上传内容。
11. **静态资源通过 `/static` 挂载**，新增前端文件后确认 wheel 中包含该文件。

## 修改指南

### 调整前端 UI

- 组件优先使用 daisyUI 类；布局和少量自定义样式使用 Tailwind / `static/style.css`。
- 保持无构建链；不要引入 npm、Vite 或 React，除非需求明确改变。
- 选区交互只允许在「原图」视图；结果和检测区视图隐藏拖拽层。
- 处理请求期间应禁用上传、模式、阈值、扩展和处理按钮，避免状态竞争。
- AI 模型不可用时，禁用 AI 模式的处理按钮，并在 `#aiHint` 提示下载命令。
- 修改 DOM id/class 时同步检查 `static/app.js` 和 `tests/test_api.py` 中的静态资源测试。

### 调整 mask / 修复算法

- 先补 `tests/test_core.py`，再改实现。
- 必须保留：ROI 越界校验、最小选区尺寸、空 mask 报错、ROI 外像素不变。
- 如果改变默认扩展、阈值或 inpaint 半径，更新 `README.md` 的实现说明和本文件。
- 大图性能与内存要保持在单机可接受范围（当前上限 25 MB / 3000 万像素）。
- 调整 AI 裁剪/缩放逻辑时，重点验证：小选区、贴边选区、大于 512 的选区、空白 mask。
- 快速模式是默认路径，任何改动都不能让它依赖模型文件。

### 修改 API

当前合约：

```text
POST /api/remove
multipart/form-data:
  file: image
  x, y, width, height: int
  threshold: int (default 200)
  expand: int 0-12 (default 6)
  mode: "fast" | "ai" (default "fast")

200 JSON:
  result, mask_overlay: data URL
  filename, width, height, detected_pixels, mode, expand, roi
```

- 参数或返回结构变化时，同步更新 `static/app.js`、`tests/test_api.py`、`README.md`。
- 用户可读错误通过 `HTTPException` 返回：参数/ROI 错误用 422，模型缺失用 503，AI 推理失败用 500。
- 不要返回服务器文件路径或内部异常堆栈。
- `GET /api/health` 包含 `ai_available`；前端用它决定 AI 模式是否可用。

## 测试要求

- 任何算法修改：覆盖正常路径、无水印、ROI 越界、选区过小、ROI 外不变。
- 任何 AI 修改：覆盖模型缺失错误；有模型时跑一次 LaMa 冒烟测试，没模型时自动 skip。
- 任何 API 修改：覆盖成功、非法 ROI、非图片输入、非法 mode、非法 expand、健康检查。
- 前端 JS 至少通过 `node --check`；涉及交互的修改应做一次浏览器手测。
- 修改依赖后运行 `uv lock`，并提交 `uv.lock`。

## 提交前检查清单

- [ ] `uv lock --check` 通过
- [ ] `uv run pytest` 全部通过
- [ ] `node --check src/oma_watermark/static/app.js` 通过
- [ ] `ruff check` / `ruff format --check` 通过（如本机可用）
- [ ] 没有提交 `.venv/`、`.artifacts/`、`models/`、`__pycache__/`、测试截图或本地图片
- [ ] README / AGENTS.md 与实际行为一致
- [ ] 新增的静态文件包含在构建产物中
- [ ] 没有引入不必要的依赖或超出 MVP 范围的功能

## 已知边界

- 单张图片、单个矩形选区
- 只支持浅色/白色水印
- 快速模式修复区域偏平滑，复杂纹理上可能有涂抹感
- AI 模式模型输入固定 512×512，大选区会被缩放；可能“脑补”背景，结果不保证与真实原图完全一致
- AI 模式首次加载模型约 8 秒，之后单张 CPU 推理约 3–4 秒（M4 Pro 实测）
- 透明 PNG 先合成白底，输出不保留 alpha
- 样式依赖 daisyUI CDN，首次加载需要联网；图片处理本身不联网
