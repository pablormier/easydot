"""Small helpers for browser-side Graphviz DOT rendering."""

from importlib.metadata import PackageNotFoundError, version as _distribution_version
from pathlib import Path

from easydot._version import UPSTREAM_PACKAGE, UPSTREAM_VERSION
from easydot._html import DotDisplay, display, html
from easydot._server import asset_base_url, asset_urls, shutdown_server


def _read_version_from_pyproject() -> str:
    pyproject = Path(__file__).resolve().parents[2] / "pyproject.toml"
    for line in pyproject.read_text(encoding="utf-8").splitlines():
        if line.startswith("version = "):
            return line.split("\"", 2)[1]
    raise RuntimeError("Unable to determine easydot version from pyproject.toml")


try:
    __version__ = _distribution_version("easydot")
except PackageNotFoundError:
    __version__ = _read_version_from_pyproject()

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
