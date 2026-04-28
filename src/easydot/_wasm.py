"""Server-side DOT rendering via wasi-graphviz WASM backend."""

from __future__ import annotations

from easydot._html import DotSource, _dot_text


def svg(dot: str | DotSource, *, engine: str = "dot") -> str:
    """Render a DOT graph to an SVG string using the wasi-graphviz WASM backend.

    Parameters
    ----------
    dot:
        A DOT source string or an object with a ``to_string()`` method.
    engine:
        Graphviz layout engine (e.g. ``dot``, ``neato``, ``circo``).

    Returns
    -------
    str
        The rendered SVG.

    Raises
    ------
    ImportError
        If the optional ``wasi-graphviz`` dependency is not installed.
    """
    dot_text = _dot_text(dot)
    try:
        import wasi_graphviz
    except ImportError as exc:
        raise ImportError(
            "The wasm backend requires the 'wasi-graphviz' package. "
            "Install it with: uv pip install 'easydot[wasm]'"
        ) from exc
    svg_bytes: bytes = wasi_graphviz.render(dot_text, format="svg", engine=engine)
    return svg_bytes.decode("utf-8")


class SvgDisplay:
    """Rich display wrapper for a static SVG rendered server-side via WASM."""

    def __init__(self, dot: str | DotSource, *, engine: str = "dot") -> None:
        self.dot = _dot_text(dot)
        self.engine = engine
        self._svg: str | None = None

    def _render(self) -> str:
        if self._svg is None:
            self._svg = svg(self.dot, engine=self.engine)
        return self._svg

    def __repr__(self) -> str:
        return self.dot

    def _repr_svg_(self) -> str:
        return self._render()

    def _repr_mimebundle_(
        self, include=None, exclude=None
    ) -> dict[str, str]:
        """Return a Jupyter MIME bundle with ``image/svg+xml``."""
        return {
            "image/svg+xml": self._render(),
            "text/plain": self.dot,
        }


def display_svg(dot: str | DotSource, *, engine: str = "dot") -> SvgDisplay:
    """Return a rich display object for a DOT graph rendered server-side.

    See :func:`svg` for parameters.
    """
    return SvgDisplay(dot, engine=engine)
