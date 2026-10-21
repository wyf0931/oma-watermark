# 安装

## 环境要求

- Python 3.12 或更新版本
- [uv](https://docs.astral.sh/uv/)
- 桌面应用需要 macOS 12+；Web 模式可在能运行 Python 和 OpenCV 的系统上使用
- 仅在重新构建 CSS 时需要 Node.js 20+

## Web 版

```bash
git clone https://github.com/wyf0931/oma-watermark.git
cd oma-watermark
uv sync
uv run oma-watermark
```

打开 <http://127.0.0.1:8000>。服务默认只监听本机地址。

快速模式无需额外依赖即可使用；AI 模式还需要下面的 LaMa 模型。

## AI 模型安装

可选模型为 [OpenCV 官方 LaMa ONNX 模型](https://huggingface.co/opencv/inpainting_lama)（约 93 MB，Apache-2.0）。只需下载一次：

```bash
uv run oma-watermark-download-model
```

模型保存到 `models/inpainting_lama_2025jan.onnx`；`models/` 已加入 `.gitignore`。

如果 Hugging Face 无法访问，先设置代理：

```bash
export https_proxy=http://127.0.0.1:7897
export http_proxy=http://127.0.0.1:7897
export all_proxy=socks5://127.0.0.1:7897
uv run oma-watermark-download-model
```

也可以直接使用 Hugging Face CLI：

```bash
uv run hf download opencv/inpainting_lama inpainting_lama_2025jan.onnx --local-dir models
```

模型放在其他位置时：

```bash
OMA_LAMA_MODEL=/path/to/inpainting_lama_2025jan.onnx uv run oma-watermark
```

Windows 构建会把模型放在应用目录内，构建脚本会自动下载。

## 桌面版依赖

macOS 桌面版使用 [pywebview](https://pywebview.flowrl.com/) 和 WKWebView。安装桌面依赖：

```bash
uv sync --extra desktop
uv run oma-watermark-desktop
```

从源码构建还需要执行 `npm ci && npm run build:css`。详见 [桌面与打包](./desktop.md)。

## 故障排查

- **AI 模式不可用或回退到快速模式** — 模型缺失或无法读取。运行下载命令并检查 `/api/health`。
- **首次 AI 请求较慢** — 模型懒加载，首次约 8 秒，之后 CPU 推理约 3–4 秒。
- **找不到 `hf` 命令** — 通过 `uv run hf` 运行，或重新执行 `uv sync`。
- **端口被占用** — 停止占用端口的进程，或重新启动应用；桌面壳会自动选择随机空闲端口。
