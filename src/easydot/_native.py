"""Server-side DOT rendering via native Graphviz executables."""

from __future__ import annotations

import subprocess

from easydot._html import DotSource, _dot_text


def native(dot: str | DotSource, *, engine: str = "dot", format: str = "svg") -> str:
    """Render a DOT graph to a string using a native Graphviz executable.

    Parameters
    ----------
    dot:
        A DOT source string or an object with a ``to_string()`` method.
    engine:
        Graphviz layout engine executable (e.g. ``dot``, ``neato``, ``circo``).
    format:
        Graphviz output format (e.g. ``svg``, ``png``, ``pdf``). Text formats
        are decoded as UTF-8.

    Returns
    -------
    str
        The rendered output decoded as UTF-8.

    Raises
    ------
    RuntimeError
        If the native Graphviz executable is unavailable or rendering fails.
    UnicodeDecodeError
        If ``format`` is binary and the output cannot be decoded as UTF-8.
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

    return result.stdout.decode("utf-8")


def native_svg(dot: str | DotSource, *, engine: str = "dot") -> str:
    """Render a DOT graph to an SVG string using native Graphviz."""
    return native(dot, engine=engine, format="svg")


class NativeSvgDisplay:
    """Rich display wrapper for a static SVG rendered by native Graphviz."""

    def __init__(self, dot: str | DotSource, *, engine: str = "dot") -> None:
        self.dot = _dot_text(dot)
        self.engine = engine
        self._svg: str | None = None

    def _render(self) -> str:
        if self._svg is None:
            self._svg = native_svg(self.dot, engine=self.engine)
        return self._svg

    def __repr__(self) -> str:
        return self.dot

    def _repr_svg_(self) -> str:
        return self._render()

    def _repr_mimebundle_(self, include=None, exclude=None) -> dict[str, str]:
        """Return a Jupyter MIME bundle with ``image/svg+xml``."""
        return {
            "image/svg+xml": self._render(),
            "text/plain": self.dot,
        }


def display_native_svg(dot: str | DotSource, *, engine: str = "dot") -> NativeSvgDisplay:
    """Return a rich display object for a DOT graph rendered by native Graphviz."""
    return NativeSvgDisplay(dot, engine=engine)
