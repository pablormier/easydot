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
