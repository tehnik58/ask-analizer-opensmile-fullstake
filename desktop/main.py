"""Desktop entrypoint — pywebview + uvicorn.

Запускает FastAPI-бэкенд в daemon-потоке на свободном порту,
затем открывает окно WebView на тот же адрес.
"""

import socket
import sys
import threading
import time
import webview

HOST = "127.0.0.1"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, 0))
        return s.getsockname()[1]


def _run_server(port: int):
    import uvicorn
    from app.main import app

    config = uvicorn.Config(app, host=HOST, port=port, log_level="warning")
    server = uvicorn.Server(config)
    server.run()


def _wait_ready(port: int, timeout: float = 15.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((HOST, port), timeout=1):
                return True
        except OSError:
            time.sleep(0.1)
    raise TimeoutError(f"Server not ready on {HOST}:{port}")


def main():
    port = _free_port()
    t = threading.Thread(target=_run_server, args=(port,), daemon=True)
    t.start()
    _wait_ready(port)

    url = f"http://{HOST}:{port}"
    window = webview.create_window(
        "Translation Confidence Analyzer",
        url,
        width=1100,
        height=850,
        min_size=(800, 600),
    )
    webview.start()


if __name__ == "__main__":
    main()
