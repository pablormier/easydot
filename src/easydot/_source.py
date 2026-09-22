"""DOT source normalization and preparation helpers.

This module intentionally contains no rendering-backend code. Keeping source
normalization here gives theme preparation a single place to run before the
backend is selected.
"""

from __future__ import annotations

from typing import Protocol, TYPE_CHECKING

if TYPE_CHECKING:
    from easydot._theme import Theme


class DotSource(Protocol):
    """Protocol for objects that can provide DOT source text."""

    def to_string(self) -> str: ...


def _dot_text(dot: str | DotSource) -> str:
    """Normalize a DOT string or a ``to_string()``-compatible object."""
    if isinstance(dot, str):
        return dot
    to_string = getattr(dot, "to_string", None)
    if not callable(to_string):
        raise TypeError("dot must be a DOT string or an object with a to_string() method")
    value = to_string()
    if not isinstance(value, str):
        raise TypeError("dot.to_string() must return a string")
    return value


def _prepare_dot(dot: str | DotSource, theme: Theme | None = None) -> str:
    """Normalize DOT and apply an optional theme exactly once.

    The helper is deliberately the boundary between user source and rendering
    backends.  Backends receive plain prepared DOT and therefore cannot apply a
    theme a second time while building rich representations or caches.
    """
    source = _dot_text(dot)
    if theme is None:
        return source
    from easydot._theme import Theme as ThemeType

    if not isinstance(theme, ThemeType):
        raise TypeError("theme must be a Theme instance or None")
    return theme.apply(source)
