"""Small helpers for browser-side Graphviz DOT rendering."""

from easydot._html import DotDisplay, display, html
from easydot._server import asset_base_url, asset_urls, shutdown_server

__all__ = [
    "DotDisplay",
    "asset_base_url",
    "asset_urls",
    "display",
    "html",
    "shutdown_server",
]

__version__ = "0.1.0"
UPSTREAM_PACKAGE = "@hpcc-js/wasm-graphviz"
UPSTREAM_VERSION = "1.21.0"
