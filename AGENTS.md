# AGENTS.md

本文件面向在本仓库工作的编码 Agent（以及人类维护者），用于快速理解项目边界、关键链路和提交前检查。修改代码前先读本文件与 `README.md`。

## 项目目标

一个本地运行的 Web 水印清除工具：

1. 用户在浏览器上传图片。
2. 用户手工框选包含水印的矩形 ROI。
3. 服务端用 OpenCV 识别 ROI 内的浅色/白色像素并生成 mask。
4. 使用 `cv2.inpaint` 修复，前端展示原图、结果和检测区，并支持下载。

产品原则是 **MVP + YAGNI**：优先保持单图片、单矩形、无账号、无数据库、无持久化。不要在没有明确需求时引入任务队列、前端构建链、对象存储、数据库或生成式模型。

## 技术栈

- Python 3.12+，`uv` 管理环境和锁文件
- FastAPI + Uvicorn
- OpenCV（`opencv-python-headless`）+ NumPy
- Pillow（EXIF 方向和透明通道处理）
- 原生 HTML/CSS/JS，无前端构建步骤
- daisyUI 5 + Tailwind CSS 4 浏览器版（CDN）
- pytest + FastAPI TestClient

## 仓库结构

```text
docs/screenshot.png              README 展示图
src/oma_watermark/__init__.py    `oma-watermark` 入口，启动 Uvicorn
src/oma_watermark/app.py         FastAPI 路由、上传限制、静态文件
src/oma_watermark/core.py        解码、mask、inpaint、编码与数据模型
src/oma_watermark/static/        Web UI（HTML / CSS / JS）
tests/test_core.py               算法与 ROI 校验测试
tests/test_api.py                API 合约与错误路径测试
pyproject.toml                   依赖、脚本、pytest 配置
uv.lock                          锁文件，修改依赖后必须更新
```

## 开发命令

```bash
uv sync                      # 安装依赖
uv run oma-watermark         # 启动 http://127.0.0.1:8000
uv run pytest                # 运行测试
uv lock --check              # 检查锁文件
node --check src/oma_watermark/static/app.js
uv build --wheel             # 可选：确认静态资源被包含进 wheel
```

提交前至少运行：

```bash
uv lock --check
uv run pytest
node --check src/oma_watermark/static/app.js
```

需要视觉验证时，启动服务后在浏览器走完：上传 → 框选 → 处理 → 切换结果/检测区 → 下载。

## 架构与数据流

```text
Browser
  ├─ 读取图片为 object URL，仅用于预览
  ├─ 在 image 上拖拽，把显示坐标换算成原图像素 ROI
  └─ POST /api/remove (multipart: file, x, y, width, height, threshold)
        ↓
FastAPI app.py
  ├─ 限制上传大小 25 MB
  ├─ 调用 core.decode_image()，处理 EXIF 方向
  ├─ 调用 core.remove_watermark()
  └─ 返回 result / mask_overlay 的 data URL + 元数据
        ↓
core.py
  ├─ ROI 内 cv2.inRange(min(B,G,R) >= threshold)
  ├─ 6px 椭圆核膨胀，覆盖抗锯齿和文字阴影
  ├─ 全图 mask 只在 ROI 内置位
  └─ cv2.inpaint(..., INPAINT_TELEA)
```

### 关键不变量

1. **ROI 坐标始终是原图像素坐标**，不是浏览器显示坐标或 CSS 像素。
   - 前端换算在 `static/app.js` 的 `pointInImage()` / `rectFromPoints()`。
   - 图片缩放后 ROI 用百分比重新渲染。
2. **mask 必须限制在 ROI 内**。ROI 外的像素不得被修改。`tests/test_core.py` 已覆盖。
3. **服务端负责 EXIF 方向**。浏览器预览与服务端解码结果必须使用同一视觉方向，否则 ROI 会错位。
4. **膨胀默认值 6**。它用于覆盖抗锯齿边缘和常见文字阴影；调低容易留下水印轮廓，调高会扩大修复面积。
5. **只检测浅色/白色水印**。`cv2.inRange` 要求 B/G/R 三个通道都高于阈值。深色水印不属于当前范围。
6. **图片在内存中处理**，不落盘、不保存历史、不记录上传内容。
7. **静态资源通过 `/static` 挂载**，新增前端文件后确认 wheel 中包含该文件。

## 修改指南

### 调整前端 UI

- 组件优先使用 daisyUI 类；布局和少量自定义样式使用 Tailwind / `static/style.css`。
- 保持无构建链；不要引入 npm、Vite 或 React，除非需求明确改变。
- 选区交互只允许在「原图」视图；结果和检测区视图隐藏拖拽层。
- 处理请求期间应禁用上传、阈值和处理按钮，避免状态竞争。
- 修改 DOM id/class 时同步检查 `static/app.js` 和 `tests/test_api.py` 中的静态资源测试。

### 调整 mask / 修复算法

- 先补 `tests/test_core.py`，再改实现。
- 必须保留：ROI 越界校验、最小选区尺寸、空 mask 报错、ROI 外像素不变。
- 如果改变默认膨胀、阈值或 inpaint 半径，更新 `README.md` 的实现说明和本文件。
- 大图性能与内存要保持在单机可接受范围（当前上限 25 MB / 3000 万像素）。

### 修改 API

当前合约：

```text
POST /api/remove
multipart/form-data:
  file: image
  x, y, width, height: int
  threshold: int (default 200)

200 JSON:
  result, mask_overlay: data URL
  filename, width, height, detected_pixels, roi
```

- 参数或返回结构变化时，同步更新 `static/app.js`、`tests/test_api.py`、`README.md`。
- 用户可读错误通过 `HTTPException(status_code=422, detail=...)` 返回。
- 不要返回服务器文件路径或内部异常堆栈。

## 测试要求

- 任何算法修改：覆盖正常路径、无水深印、ROI 越界、选区过小、ROI 外不变。
- 任何 API 修改：覆盖成功、非法 ROI、非图片输入、健康检查。
- 前端 JS 至少通过 `node --check`；涉及交互的修改应做一次浏览器手测。
- 修改依赖后运行 `uv lock`，并提交 `uv.lock`。

## 提交前检查清单

- [ ] `uv lock --check` 通过
- [ ] `uv run pytest` 全部通过
- [ ] `node --check src/oma_watermark/static/app.js` 通过
- [ ] 没有提交 `.venv/`、`.artifacts/`、`__pycache__/`、测试截图或本地图片
- [ ] README / AGENTS.md 与实际行为一致
- [ ] 新增的静态文件包含在构建产物中
- [ ] 没有引入不必要的依赖或超出 MVP 范围的功能

## 已知边界

- 单张图片、单个矩形选区
- 只支持浅色/白色水印
- 透明 PNG 先合成白底，输出不保留 alpha
- 修复结果依赖背景纹理，复杂区域可能有涂抹感
- 样式依赖 daisyUI CDN，首次加载需要联网；图片处理本身不联网
