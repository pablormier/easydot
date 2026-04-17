"""Serve bundled browser assets from a process-local loopback HTTP server."""

from __future__ import annotations

import atexit
import mimetypes
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from urllib.parse import unquote, urlsplit

_ASSET_PACKAGE = "easydot.assets"
_ALLOWED_FILES = frozenset(
    {
        "index.js",
        "LICENSE.hpcc-js-wasm",
        "package.json",
        "README.hpcc-js-wasm.md",
    }
)

_LOCK = threading.Lock()
_SERVER: ThreadingHTTPServer | None = None
_THREAD: threading.Thread | None = None
_BASE_URL: str | None = None


class _AssetHandler(BaseHTTPRequestHandler):
    server_version = "easydot"

    def do_GET(self) -> None:
        self._serve(head_only=False)

    def do_HEAD(self) -> None:
        self._serve(head_only=True)

    def log_message(self, fmt: str, *args: object) -> None:
        return

    def _serve(self, *, head_only: bool) -> None:
        name = unquote(urlsplit(self.path).path).lstrip("/")
        if name not in _ALLOWED_FILES or "/" in name:
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        asset = files(_ASSET_PACKAGE).joinpath(name)
        if not asset.is_file():
            self.send_error(HTTPStatus.SERVICE_UNAVAILABLE)
            return

        data = asset.read_bytes()
        content_type, _encoding = mimetypes.guess_type(name)
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type or "application/octet-stream")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "public, max-age=31536000, immutable")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        if not head_only:
            self.wfile.write(data)


def asset_base_url() -> str:
    """Start or reuse the local asset server and return its base URL."""

    global _BASE_URL, _SERVER, _THREAD

    with _LOCK:
        if _BASE_URL is not None:
            return _BASE_URL

        server = ThreadingHTTPServer(("127.0.0.1", 0), _AssetHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True, name="easydot-assets")
        thread.start()

        _SERVER = server
        _THREAD = thread
        _BASE_URL = f"http://127.0.0.1:{server.server_address[1]}"
        atexit.register(shutdown_server)
        return _BASE_URL


def asset_urls() -> dict[str, str]:
    """Return URLs for the bundled browser assets."""

    base_url = asset_base_url()
    return {
        "js": f"{base_url}/index.js",
        "license": f"{base_url}/LICENSE.hpcc-js-wasm",
        "package": f"{base_url}/package.json",
        "readme": f"{base_url}/README.hpcc-js-wasm.md",
    }


def shutdown_server() -> None:
    """Stop the local asset server if it is running."""

    global _BASE_URL, _SERVER, _THREAD

    with _LOCK:
        server = _SERVER
        thread = _THREAD
        _SERVER = None
        _THREAD = None
        _BASE_URL = None

        if server is not None:
            server.shutdown()
            server.server_close()
        if thread is not None and thread.is_alive():
            thread.join(timeout=2)
