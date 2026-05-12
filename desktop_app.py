from __future__ import annotations

import argparse
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

from core.config import load_config
from core.web_service import find_free_port as _find_free_port
from core.web_service import serve_in_background
from web_app import build_server


def find_free_port(preferred: int = 8765) -> int:
    return _find_free_port(preferred)


def start_server(project_dir: Path, config: dict, port: int) -> ThreadingHTTPServer:
    server = build_server(config, project_dir, "127.0.0.1", port)
    serve_in_background(server)
    return server


def main() -> int:
    parser = argparse.ArgumentParser(description="Desktop app wrapper for the voice agent.")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--hidden", action="store_true", help="Run the local service only, without opening a window.")
    args = parser.parse_args()

    project_dir = Path(__file__).resolve().parent
    config = load_config(project_dir / args.config)
    port = find_free_port(args.port)
    server = start_server(project_dir, config, port)
    url = f"http://127.0.0.1:{port}"

    if args.hidden:
        print(f"Voice Agent service running at {url}")
        threading.Event().wait()
        return 0

    import webview

    window = webview.create_window(
        "实时语音 Agent",
        url,
        width=1160,
        height=780,
        min_size=(900, 640),
        text_select=True,
    )
    try:
        webview.start(debug=False)
    finally:
        server.shutdown()
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
