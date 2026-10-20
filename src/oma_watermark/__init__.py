"""Run the watermark remover with `uv run oma-watermark`."""

import uvicorn


def main() -> None:
    uvicorn.run("oma_watermark.app:app", host="127.0.0.1", port=8000)
