# 水印清除器

[English](README.md) | **简体中文**

[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-3776AB.svg)](https://www.python.org/)
[![Build desktop apps](https://github.com/wyf0931/oma-watermark/actions/workflows/build-desktop.yml/badge.svg)](https://github.com/wyf0931/oma-watermark/actions/workflows/build-desktop.yml)

本地运行的水印清除工具：用 OpenCV 识别浅色水印，可选 LaMa AI 精修。

上传图片，框出水印区域，程序会识别选区内的浅色像素并完成修复。图片只在本机内存中处理，不经过第三方服务。Web 界面与 macOS 桌面应用共用同一套 FastAPI + HTML/CSS/JS 实现。

![macOS 桌面模式下 AI 精修后的图片结果](docs/screenshot.png)

*macOS 桌面模式。原生标题栏由 macOS 提供，不属于网页界面。*

## 特性

- **本地处理** — 图片不落盘、不上传、不留历史。
- **两种修复引擎** — 默认使用 LaMa AI 精修；模型不可用时自动回退到 OpenCV 快速修复。
- **可控的矩形选区** — 只修改选区内的像素，阈值和边缘扩展可调。
- **Web 与桌面** — 可在浏览器运行，也有原生 macOS 应用，另提供可选的 Windows ZIP 构建。
- **结果与检测预览** — 对比修复结果和检测到的水印区域，确认后下载。

## 快速开始

需要 Python 3.12+ 和 [uv](https://docs.astral.sh/uv/)。

```bash
uv sync
uv run oma-watermark
```

打开 <http://127.0.0.1:8000>。

AI 精修使用 [OpenCV 官方 LaMa ONNX 模型](https://huggingface.co/opencv/inpainting_lama)（约 93 MB），只需下载一次：

```bash
uv run oma-watermark-download-model
```

快速模式不需要模型。如果 Hugging Face 无法访问，见 [AI 模型安装](docs/zh-CN/install.md#ai-模型安装)。

## 使用步骤

1. 拖入或选择一张图片（PNG / JPEG / WebP / BMP，≤ 25 MB）。
2. 在原图上拖动鼠标，框出包含水印的矩形。
3. 复杂背景优先用 **AI · LaMa**，简单背景可切换到 **快速 · OpenCV**；模型缺失时会自动回退到快速模式。
4. 按需调整 **亮度阈值** 和 **边缘扩展**。
5. 开始修复，在 **结果 / 检测** 之间切换，确认后下载。

**亮度阈值** — B、G、R 三个通道都高于该值的像素会被当作水印。没清干净就调低；误选背景就调高。

**边缘扩展** — 向外扩展 mask，覆盖白边、阴影和抗锯齿。默认 6 px，范围 0–12。

## 桌面应用

从 [GitHub Releases](https://github.com/wyf0931/oma-watermark/releases) 下载 `Watermark-Remover-*.dmg`，打开后把应用拖入 Applications。DMG 内置 LaMa 模型，AI 模式可离线使用。当前构建为 ad-hoc 签名、未公证；首次打开可能需要右键应用并选择「打开」。

本地桌面运行、打包、Windows 构建和 CI 说明见 [桌面与打包](docs/zh-CN/desktop.md)。

## 实现方式

1. 前端把图片、ROI、阈值、扩展值和模式发送到 `POST /api/remove`。
2. 服务端用 `cv2.inRange` 选中 ROI 内的浅色像素，并对 mask 做膨胀。
3. **快速**模式使用 `cv2.inpaint(..., cv2.INPAINT_TELEA)`；**AI** 模式裁出 mask 周围的正方形区域，通过 OpenCV DNN 以 512×512 运行 LaMa，再把 mask 内像素贴回原图。
4. API 返回结果图、红色检测区预览和元数据。

完整流程和代码地图见 [架构](docs/zh-CN/architecture.md)。

## 文档

| 文档 | 内容 |
| --- | --- |
| [安装](docs/zh-CN/install.md) | Web 环境、AI 模型下载、代理、桌面依赖 |
| [桌面与打包](docs/zh-CN/desktop.md) | DMG/Windows 构建、GitHub Actions、签名 |
| [架构](docs/zh-CN/architecture.md) | 处理流程、关键不变量、项目结构、UI 主题 |
| [API](docs/zh-CN/api.md) | `POST /api/remove`、`GET /api/health`、错误码 |
| [开发](docs/zh-CN/development.md) | 测试、lint、CSS 构建、贡献流程 |
| [FAQ 与边界](docs/zh-CN/faq.md) | 支持的输入、已知限制、故障排查 |

English documentation: [README](README.md) · [docs](docs/).

## 项目结构

```text
src/oma_watermark/     FastAPI、核心算法、LaMa、桌面壳、Web UI
packaging/             PyInstaller spec、图标、DMG/Windows 构建脚本
tests/                 算法与 API 测试
docs/                  详细文档与截图
```

## 贡献

欢迎提交 Issue 和 Pull Request。较大的改动请先开 Issue 讨论方案。提交前请运行 [开发文档](docs/zh-CN/development.md#检查清单) 中的检查项。

## 许可证

[MIT](LICENSE) © 2026 Scott。内置 LaMa 模型采用 Apache-2.0 许可。
