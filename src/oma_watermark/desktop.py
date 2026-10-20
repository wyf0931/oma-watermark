"""Native desktop shell for the watermark remover."""

from __future__ import annotations

import html
import http.client
import logging
import multiprocessing
import os
import socket
import sys
import threading
import time
from pathlib import Path

import uvicorn

from .app import app

HOST = "127.0.0.1"
STARTUP_TIMEOUT = 20


def _log_path() -> Path:
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Logs"
    elif sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "WatermarkRemover"
    else:
        base = Path.home() / ".local" / "state" / "oma-watermark"
    return base / "WatermarkRemover.log"


def _configure_logging() -> Path:
    path = _log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=path,
        encoding="utf-8",
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    return path


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((HOST, 0))
        return int(sock.getsockname()[1])


def _wait_for_server(port: int, timeout: float = STARTUP_TIMEOUT) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        connection: http.client.HTTPConnection | None = None
        try:
            connection = http.client.HTTPConnection(HOST, port, timeout=0.5)
            connection.request("GET", "/api/health")
            response = connection.getresponse()
            response.read()
            if response.status == 200:
                return
        except OSError:
            pass
        finally:
            if connection is not None:
                connection.close()
        time.sleep(0.1)
    raise RuntimeError(f"本地服务未能在 {timeout:.0f} 秒内启动")


def _show_error(webview: object, message: str) -> None:
    escaped = html.escape(message)
    window = webview.create_window(  # type: ignore[attr-defined]
        "水印清除器",
        html=(
            "<main style='font-family:-apple-system,BlinkMacSystemFont,sans-serif;"
            "padding:32px;color:#1d1d1f'>"
            "<h1 style='font-size:21px'>启动失败</h1>"
            f"<pre style='white-space:pre-wrap;color:#d70015'>{escaped}</pre>"
            "<p style='color:#7a7a7a'>日志：" + html.escape(str(_log_path())) + "</p>"
            "</main>"
        ),
        width=620,
        height=380,
    )
    webview.start()  # type: ignore[attr-defined]
    _ = window


def main() -> None:
    multiprocessing.freeze_support()
    log_path = _configure_logging()

    try:
        import webview
    except ImportError as exc:
        logging.exception("pywebview is not installed")
        raise SystemExit("请安装桌面依赖：uv sync --extra desktop") from exc

    webview.settings["ALLOW_DOWNLOADS"] = True

    port = _free_port()
    config = uvicorn.Config(
        app,
        host=HOST,
        port=port,
        log_level="warning",
        access_log=False,
    )
    server = uvicorn.Server(config)
    server_thread = threading.Thread(target=server.run, name="oma-server", daemon=True)

    try:
        server_thread.start()
        _wait_for_server(port)
        webview.create_window(
            "水印清除器",
            f"http://{HOST}:{port}/?desktop=1",
            width=1240,
            height=860,
            min_size=(980, 700),
            background_color="#f5f5f7",
            zoomable=True,
        )
        webview.start(debug=os.environ.get("OMA_DESKTOP_DEBUG") == "1")
    except Exception as exc:
        logging.exception("Desktop startup failed")
        _show_error(webview, f"{exc}\n\n完整日志：{log_path}")
    finally:
        server.should_exit = True
        server_thread.join(timeout=5)


if __name__ == "__main__":
    main()
