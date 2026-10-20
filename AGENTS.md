# AGENTS.md

本文件面向在本仓库工作的编码 Agent（以及人类维护者），用于快速理解项目边界、关键链路和提交前检查。修改代码前先读本文件、`README.md` 和 `DESIGN.md`。

## 项目目标

一个本地运行的水印清除工具，提供 Web 版和 macOS 桌面版：

1. 用户在浏览器或原生窗口上传图片。
2. 用户手工框选包含水印的矩形 ROI。
3. 服务端用 OpenCV 识别 ROI 内的浅色/白色像素并生成 mask。
4. 用户选择修复引擎：
   - `ai`：默认（模型可用时），OpenCV DNN + LaMa ONNX，更擅长恢复纹理。
   - `fast`：模型不可用或用户主动选择时使用，`cv2.inpaint`，无需模型。
5. 前端展示原图、结果和检测区，并支持下载。

产品原则是 **MVP + YAGNI**：单图片、单矩形、无账号、无数据库、无持久化。默认体验使用 AI 精修；模型不可用时自动回退快速模式，不能破坏纯 Web / 快速模式的可用性。

## 技术栈

- Python 3.12+，`uv` 管理环境和锁文件
- FastAPI + Uvicorn，本地随机端口
- OpenCV（`opencv-python-headless`）+ NumPy + Pillow
- LaMa ONNX 通过 `cv2.dnn` 运行，无 PyTorch / ONNX Runtime
- pywebview（WKWebView / WebView2）作为桌面壳
- PyInstaller 打包 `.app` / Windows ZIP；`hdiutil` 生成 DMG
- 原生 HTML/CSS/JS
- Tailwind CSS 4 + daisyUI 5，本地构建，不使用 CDN
- pytest + FastAPI TestClient
- GitHub Actions 构建 macOS DMG 和可选 Windows ZIP

## 仓库结构

```text
DESIGN.md                        Apple 设计语言参考
docs/screenshot.png              README 展示图（macOS 桌面模式）
src/oma_watermark/__init__.py    `oma-watermark` Web 入口
src/oma_watermark/app.py         FastAPI 路由、上传限制、静态资源、健康检查
src/oma_watermark/core.py        解码、mask、快速修复、编码与数据模型
src/oma_watermark/lama.py        LaMa 模型定位、懒加载、裁剪推理与错误类型
src/oma_watermark/desktop.py     pywebview 窗口、本地服务生命周期、下载开关
src/oma_watermark/download_model.py  `oma-watermark-download-model`
src/oma_watermark/static/
  app.css                        Tailwind 入口 + daisyUI apple/apple-dark 主题
  app.built.css                  由 npm run build:css 生成，提交到仓库
  index.html                    Web / 桌面共用页面
  app.js                        ROI、模式、请求、下载、桌面检测
  style.css                     图片画布、桌面模式、Apple 细节样式
packaging/
  desktop_entry.py              PyInstaller 入口
  oma-watermark.spec            PyInstaller spec
  build_macos.sh                DMG 构建脚本
  build_windows.ps1             Windows ZIP 构建脚本
  icon.icns / icon.ico / icon.png
tests/test_core.py              算法、mask、AI 缺失/冒烟测试
tests/test_api.py               API 合约与错误路径测试
.github/workflows/build-desktop.yml  macOS / Windows 桌面构建
models/                         本地下载的模型，已 gitignore
```

## 开发命令

```bash
uv sync                              # Web / 测试依赖
uv run oma-watermark                 # Web 版 http://127.0.0.1:8000
uv run oma-watermark-download-model  # 下载可选 LaMa 模型
uv run pytest                        # 测试
uv lock --check
node --check src/oma_watermark/static/app.js
ruff check src tests
ruff format --check src tests

npm ci                               # 前端 CSS 构建依赖
npm run build:css                    # 生成 app.built.css
npm run watch:css                    # 开发时监听 CSS

uv sync --extra desktop
uv run oma-watermark-desktop         # 本地原生窗口

bash packaging/build_macos.sh        # 本地构建 DMG
powershell -ExecutionPolicy Bypass -File packaging/build_windows.ps1
```

下载模型需要 `hf` CLI（项目依赖 `huggingface-hub` 已包含）。若 Hugging Face 无法访问：

```bash
export https_proxy=http://127.0.0.1:7897
export http_proxy=http://127.0.0.1:7897
export all_proxy=socks5://127.0.0.1:7897
uv run oma-watermark-download-model
```

提交前至少运行：

```bash
npm run build:css
ruff check src tests
ruff format --check src tests
uv lock --check
uv run pytest
node --check src/oma_watermark/static/app.js
```

需要视觉验证时：

- Web：启动服务，在浏览器检查上传 → 框选 → 快速/AI → 结果/检测区。
- Desktop：`uv run oma-watermark-desktop`，确认隐藏网页 navbar、原生标题栏、下载可用。
- 打包：至少执行一次 `bash packaging/build_macos.sh`，启动 `.app`，请求 `/api/health` 和一次 AI 推理（内置模型）。

## 架构与数据流

```text
Web browser ───────────────┐
                           ├─ GET /api/health
macOS pywebview window ────┤   POST /api/remove
  (http://127.0.0.1:<随机端口>/?desktop=1)
                           ↓
FastAPI app.py
  ├─ 限制上传大小 25 MB，校验 mode
  ├─ core.decode_image()，处理 EXIF
  ├─ core.remove_watermark(..., engine=mode)
  │    ├─ fast: cv2.inpaint(TELEA)
  │    └─ ai:   lama.inpaint_with_lama()
  └─ result / mask_overlay data URL + 元数据
```

桌面启动流程：

```text
oma-watermark-desktop
  ├─ 配置日志：~/Library/Logs/WatermarkRemover.log（macOS）
  ├─ 绑定 127.0.0.1 的随机端口
  ├─ 后台线程启动 Uvicorn
  ├─ 轮询 /api/health
  ├─ 创建 pywebview 窗口 → /?desktop=1
  ├─ 设置 ALLOW_DOWNLOADS=True，允许保存结果图
  └─ 窗口关闭 → server.should_exit=True
```

### 关键不变量

1. **ROI 坐标始终是原图像素坐标**，不是 CSS 像素。
   - 前端换算在 `static/app.js` 的 `pointInImage()` / `rectFromPoints()`。
2. **mask 必须限制在 ROI 内**。ROI 外像素不得被修改，测试已覆盖。
3. **服务端负责 EXIF 方向**，否则浏览器预览和服务端 ROI 会错位。
4. **`expand` 合法范围 0–12，默认 6**，用于覆盖白边、阴影和抗锯齿。
5. **只检测浅色/白色水印**。`cv2.inRange` 要求 B/G/R 都高于阈值。
6. **AI 模型是可选资源**。开发模式下默认 `models/inpainting_lama_2025jan.onnx`，`OMA_LAMA_MODEL` 可覆盖；冻结模式下默认读取 `sys._MEIPASS/models/...`。
7. **AI 模型懒加载并串行推理**，`lama.py` 用锁保护模型加载和 `cv2.dnn` 推理。
8. **AI 只贴回 mask 内像素**，mask 外必须保持原图。
9. **默认模式是 AI**：UI 在健康检查通过后默认选择 `ai`，API 默认也是 `ai`；模型缺失时 UI 自动回退 `fast`，Web 和桌面仍可正常使用。用户手动切换后（`modeTouched`）不要被异步健康检查覆盖。
10. **CSS 不手改 `app.built.css`**。修改 `app.css`、`index.html`、`style.css` 后运行 `npm run build:css`，并提交生成文件。
11. **Apple 主题通过 daisyUI theme plugin 定义**：`apple` 为默认浅色，`apple-dark` 为 `prefersdark`。不要退回 CDN 或 Tailwind browser 运行时。
12. **桌面模式用 `?desktop=1` 标记**，`html[data-desktop="true"]` 隐藏 `#appHeader`，使用原生标题栏。
13. **桌面窗口默认 1240×880，最小 980×780**，通过 `?desktop=1` 隐藏 navbar；桌面模式隐藏页面滚动条，效果提示放在工具栏的「?」帮助弹窗，不占右侧空间。
14. **冻结资源路径**：`app.py` 的 `_static_dir()` 和 `lama.py` 的 `_default_model_path()` 负责 PyInstaller 的 `_MEIPASS` 路径，修改时必须在打包后验证。
15. **桌面下载**：pywebview 必须设置 `webview.settings["ALLOW_DOWNLOADS"] = True`，否则下载按钮无效。
16. **图片在内存中处理**，不落盘、不保存历史、不记录上传内容。

## 修改指南

### 调整前端 UI / 主题

- 组件优先使用 daisyUI；布局和细节用 Tailwind / `style.css`。
- Apple 设计 token 参考 `DESIGN.md`：Action Blue #0066cc、Parchment #f5f5f7、18px 卡片圆角、胶囊按钮、无卡片阴影。
- 主题只写在 `app.css` 的 `@plugin "daisyui/theme"` 中；新增/修改后运行 `npm run build:css`。
- 不要引入 CSS 框架 CDN；桌面应用必须离线可用。
- 选中框、图片画布、桌面模式样式在 `style.css`。
- 修改 DOM id/class 时同步检查 `static/app.js` 和 `tests/test_api.py` 静态资源测试。
- 桌面模式不要显示网站 navbar；需要品牌信息时交给 macOS 原生标题栏。

### 调整 mask / 修复算法

- 先补 `tests/test_core.py`，再改实现。
- 必须保留：ROI 越界、最小选区、空 mask 报错、ROI 外不变。
- 改变默认扩展、阈值或 inpaint 半径时，更新 README 和本文件。
- AI 裁剪/缩放逻辑修改后验证：小选区、贴边选区、大于 512 的选区、空白 mask。
- 大图内存上限保持 25 MB / 3000 万像素。

### 修改 API

```text
POST /api/remove
multipart/form-data:
  file: image
  x, y, width, height: int
  threshold: int (default 200)
  expand: int 0-12 (default 6)
  mode: "ai" | "fast" (default "ai")

200 JSON:
  result, mask_overlay: data URL
  filename, width, height, detected_pixels, mode, expand, roi
```

- 参数或返回结构变化时同步更新 `app.js`、`tests/test_api.py`、`README.md`。
- 422：参数/ROI 错误；503：模型缺失（UI 会回退 fast）；500：AI 推理失败。
- `GET /api/health` 包含 `ai_available` 和 `ai_engine`。

### 修改桌面 / 打包

- 桌面入口：`src/oma_watermark/desktop.py`；PyInstaller 入口：`packaging/desktop_entry.py`。
- 新增静态文件/模型资源时，必须同步 `packaging/oma-watermark.spec` 的 `datas`。
- 新增 Python 包时，确认 PyInstaller 能收集；必要时加入 `hiddenimports`。
- 修改构建脚本后，本地至少执行一次 DMG 构建并启动 `.app`。
- DMG 是 ad-hoc 签名；不要把证书、密码或签名密钥写入仓库。
- `OMA_APP_VERSION` 控制 Info.plist 和产物版本号。

## 测试要求

- 算法修改：正常路径、无水印、ROI 越界、选区过小、ROI 外不变。
- AI 修改：模型缺失错误；有模型时 LaMa 冒烟测试；无模型时自动 skip。
- API 修改：成功、非法 ROI、非图片、非法 mode、非法 expand、健康检查。
- 前端：`node --check`，并做一次 Web + 桌面模式手测，确认默认 AI、帮助弹窗、桌面无右侧滚动条。
- 主题/样式：`npm run build:css` 后检查浅色/深色和桌面 navbar 隐藏。
- 打包：启动 `.app`，确认 `/api/health`、静态资源、AI 推理和下载。

## 提交前检查清单

- [ ] `npm run build:css`，`app.built.css` 已更新
- [ ] `ruff check` / `ruff format --check` 通过
- [ ] `uv lock --check` 通过
- [ ] `uv run pytest` 全部通过
- [ ] `node --check src/oma_watermark/static/app.js` 通过
- [ ] 没有提交 `.venv/`、`.artifacts/`、`models/`、`build/`、`dist/`、`node_modules/`
- [ ] README / AGENTS.md / DESIGN.md 与实际行为一致
- [ ] 新增静态文件/模型资源包含在 PyInstaller spec
- [ ] 桌面模式隐藏 navbar，下载按钮可用
- [ ] macOS DMG 构建成功且 `.app` 能启动

## 已知边界

- 单张图片、单个矩形选区
- 只支持浅色/白色水印
- 快速模式修复区域偏平滑，复杂纹理可能有涂抹感
- AI 输入固定 512×512，大选区会被缩放，可能“脑补”背景
- AI 首次加载约 8 秒，之后 CPU 推理约 3–4 秒（M4 Pro 实测）
- macOS DMG 为 ad-hoc 签名、未公证；首次打开可能需要右键 → 打开
- Windows ZIP 依赖 WebView2，不是安装器
- 透明 PNG 先合成白底，输出不保留 alpha
- 图片处理不联网，但首次下载 AI 模型需要访问 Hugging Face
