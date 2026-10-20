"""Download the optional OpenCV LaMa ONNX model from Hugging Face."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from .lama import DEFAULT_MODEL_PATH, MIN_MODEL_BYTES, MODEL_FILENAME, MODEL_REPO


def _is_ready(path: Path) -> bool:
    try:
        return path.is_file() and path.stat().st_size >= MIN_MODEL_BYTES
    except OSError:
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description="下载可选的 LaMa 水印修复模型")
    parser.add_argument(
        "--output",
        type=Path,
        help="模型保存路径（默认 models/inpainting_lama_2025jan.onnx，也可用 OMA_LAMA_MODEL）",
    )
    parser.add_argument("--force", action="store_true", help="即使模型已存在也重新下载")
    args = parser.parse_args()

    configured = args.output or (
        Path(os.environ["OMA_LAMA_MODEL"]).expanduser()
        if os.environ.get("OMA_LAMA_MODEL")
        else DEFAULT_MODEL_PATH
    )
    target = configured.expanduser().resolve()

    if _is_ready(target) and not args.force:
        print(f"Model already ready: {target}")
        print("Start the app with: uv run oma-watermark")
        return

    hf = shutil.which("hf")
    if hf is None:
        print(
            "Error: 未找到 hf 命令。请先运行 uv sync（项目已包含 huggingface-hub），"
            "或参考 https://huggingface.co/docs/huggingface_hub/guides/cli",
            file=sys.stderr,
        )
        raise SystemExit(1)

    target.parent.mkdir(parents=True, exist_ok=True)
    print(
        f"Downloading {MODEL_REPO}/{MODEL_FILENAME} from Hugging Face ...", flush=True
    )
    with tempfile.TemporaryDirectory(prefix="oma-lama-", dir=target.parent) as temp_dir:
        command = [
            hf,
            "download",
            MODEL_REPO,
            MODEL_FILENAME,
            "--local-dir",
            temp_dir,
        ]
        try:
            completed = subprocess.run(command)
        except OSError as exc:
            print(f"Error: 无法运行 hf 命令：{exc}", file=sys.stderr)
            raise SystemExit(1) from exc
        if completed.returncode != 0:
            print(
                "Error: 下载失败。如果 Hugging Face 无法访问，请先设置代理：\n"
                "  export https_proxy=http://127.0.0.1:7897\n"
                "  export http_proxy=http://127.0.0.1:7897\n"
                "  uv run oma-watermark-download-model",
                file=sys.stderr,
            )
            raise SystemExit(1)

        downloaded = next(Path(temp_dir).rglob(MODEL_FILENAME), None)
        if downloaded is None or not _is_ready(downloaded):
            print("Error: 下载的文件不完整。", file=sys.stderr)
            raise SystemExit(1)

        try:
            os.replace(downloaded, target)
        except OSError as exc:
            print(f"Error: 无法保存模型：{exc}", file=sys.stderr)
            raise SystemExit(1) from exc

    print(f"Model ready: {target}")
    print("Start the app with: uv run oma-watermark")
    print("Then choose “AI 精修 · LaMa” in the UI.")


if __name__ == "__main__":
    main()
