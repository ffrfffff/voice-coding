from __future__ import annotations

import socket
import threading
from http.server import ThreadingHTTPServer


def find_free_port(preferred: int = 8765, host: str = "127.0.0.1") -> int:
    if _port_available(preferred, host):
        return preferred
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return int(sock.getsockname()[1])


def _port_available(port: int, host: str) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind((host, port))
        except OSError:
            return False
    return True


def serve_in_background(server: ThreadingHTTPServer) -> threading.Thread:
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return thread
