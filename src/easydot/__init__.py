"""Small helpers for browser-side Graphviz DOT rendering."""

from importlib.metadata import version as _distribution_version

from easydot._version import UPSTREAM_PACKAGE, UPSTREAM_VERSION
from easydot._html import DotDisplay, display, html
from easydot._native import NativeSvgDisplay, display_native_svg, native, native_svg
from easydot._server import asset_base_url, asset_urls, shutdown_server
from easydot._wasm import SvgDisplay, display_svg, svg

__version__ = _distribution_version("easydot")


def render(
    dot: str | object, *, backend: str = "browser", **kwargs
) -> DotDisplay | SvgDisplay | NativeSvgDisplay:
    """Return a rich display object for a DOT graph.

    Parameters
    ----------
    dot:
        A DOT source string or an object with a ``to_string()`` method.
    backend:
        ``"browser"`` for interactive browser-side rendering
        (returns ``DotDisplay``), ``"wasm"`` for static server-side
        WASM SVG rendering (returns ``SvgDisplay``), or ``"native"``
        for static SVG rendering via native Graphviz
        (returns ``NativeSvgDisplay``).
    **kwargs:
        Forwarded to the underlying backend function.

    Returns
    -------
    DotDisplay, SvgDisplay, or NativeSvgDisplay
    """
    if backend == "browser":
        return display(dot, **kwargs)
    if backend == "wasm":
        return display_svg(dot, **kwargs)
    if backend == "native":
        return display_native_svg(dot, **kwargs)
    raise ValueError(f"backend must be 'browser', 'wasm', or 'native'; got {backend!r}")


def to_string(dot: str | object, *, backend: str = "browser", **kwargs) -> str:
    """Render a DOT graph to a string.

    Parameters
    ----------
    dot:
        A DOT source string or an object with a ``to_string()`` method.
    backend:
        ``"browser"`` for an HTML string (via :func:`html`),
        ``"wasm"`` for an SVG string (via :func:`svg`), or
        ``"native"`` for an SVG string (via :func:`native_svg`).
    **kwargs:
        Forwarded to the underlying backend function.

    Returns
    -------
    str
    """
    if backend == "browser":
        return html(dot, **kwargs)
    if backend == "wasm":
        return svg(dot, **kwargs)
    if backend == "native":
        return native_svg(dot, **kwargs)
    raise ValueError(f"backend must be 'browser', 'wasm', or 'native'; got {backend!r}")


__all__ = [
    "DotDisplay",
    "NativeSvgDisplay",
    "SvgDisplay",
    "UPSTREAM_PACKAGE",
    "UPSTREAM_VERSION",
    "__version__",
    "asset_base_url",
    "asset_urls",
    "display",
    "display_native_svg",
    "display_svg",
    "html",
    "native",
    "native_svg",
    "render",
    "shutdown_server",
    "svg",
    "to_string",
]
