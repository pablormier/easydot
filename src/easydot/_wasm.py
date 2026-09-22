"""Server-side DOT rendering via wasi-graphviz WASM backend."""

from __future__ import annotations

from easydot._source import DotSource, _dot_text


def render(
    dot: str | DotSource,
    *,
    format: str = "svg",
    engine: str = "dot",
) -> str | bytes:
    """Render a DOT graph using the wasi-graphviz WASM backend.

    Parameters
    ----------
    dot:
        A DOT source string or an object with a ``to_string()`` method.
    format:
        Graphviz output format, such as ``"svg"`` or ``"png"``.
    engine:
        Graphviz layout engine (e.g. ``dot``, ``neato``, ``circo``).

    Returns
    -------
    str or bytes
        Text output for SVG and bytes for binary formats.

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
    rendered: bytes = wasi_graphviz.render(dot_text, format=format, engine=engine)
    if format == "svg":
        return rendered.decode("utf-8")
    return rendered


def svg(dot: str | DotSource, *, engine: str = "dot") -> str:
    """Render a DOT graph to an SVG string using the WASM backend."""
    rendered = render(dot, format="svg", engine=engine)
    assert isinstance(rendered, str)
    return rendered
