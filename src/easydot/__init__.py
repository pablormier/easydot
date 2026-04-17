"""Small helpers for browser-side Graphviz DOT rendering."""

from easydot._version import UPSTREAM_PACKAGE, UPSTREAM_VERSION, __version__
from easydot._html import DotDisplay, display, html
from easydot._server import asset_base_url, asset_urls, shutdown_server

__all__ = [
    "DotDisplay",
    "UPSTREAM_PACKAGE",
    "UPSTREAM_VERSION",
    "__version__",
    "asset_base_url",
    "asset_urls",
    "display",
    "html",
    "shutdown_server",
]
