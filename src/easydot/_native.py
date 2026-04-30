"""Server-side DOT rendering via native Graphviz executables."""

from __future__ import annotations

import subprocess

from easydot._html import DotSource, _dot_text

_TEXT_FORMATS = frozenset({"svg", "dot", "plain", "json", "xdot", "xdot1.2", "xdot1.4", "ps", "eps"})


def native(dot: str | DotSource, *, engine: str = "dot", format: str = "svg") -> str | bytes:
    """Render a DOT graph using a native Graphviz executable.

    Parameters
    ----------
    dot:
        A DOT source string or an object with a ``to_string()`` method.
    engine:
        Graphviz layout engine executable (e.g. ``dot``, ``neato``, ``circo``).
    format:
        Graphviz output format (e.g. ``svg``, ``png``, ``pdf``).
        Text formats are returned as ``str``; binary formats as ``bytes``.

    Returns
    -------
    str or bytes
        The rendered output. ``str`` for text formats, ``bytes`` for binary
        formats (e.g. ``png``, ``pdf``).

    Raises
    ------
    RuntimeError
        If the native Graphviz executable is unavailable or rendering fails.
    """
    dot_text = _dot_text(dot)
    try:
        result = subprocess.run(
            [engine, f"-T{format}"],
            input=dot_text.encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            f"Native Graphviz executable {engine!r} was not found. "
            "Install Graphviz and ensure the executable is on PATH."
        ) from exc

    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace").strip()
        detail = f": {stderr}" if stderr else ""
        raise RuntimeError(f"Native Graphviz {engine!r} failed{detail}")

    if format in _TEXT_FORMATS:
        return result.stdout.decode("utf-8")
    return result.stdout


def native_svg(dot: str | DotSource, *, engine: str = "dot") -> str:
    """Render a DOT graph to an SVG string using native Graphviz."""
    result = native(dot, engine=engine, format="svg")
    assert isinstance(result, str)
    return result
