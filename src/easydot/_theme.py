"""Composable Graphviz default styles."""

from __future__ import annotations

import math
import re
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from easydot._source import DotSource, _dot_text


AttributeValue = str | int | float | bool


# Graphviz IDs can be alphabetic/underscore identifiers or numeral IDs. Theme
# attribute names use this policy even though generated keys are quoted, so
# malformed keys are rejected before they reach Graphviz.
_DOT_ID = re.compile(
    r"(?:[A-Za-z_\x80-\uffff][A-Za-z0-9_\x80-\uffff]*|-?(?:\d+(?:\.\d*)?|\.\d+))\Z"
)
_ESCSTRING_ESCAPES = frozenset("NGETHLnlr")


def _is_header_id_char(char: str) -> bool:
    return char == "_" or char.isalnum() or ord(char) >= 128


def _validate_attr_key(key: object) -> str:
    if not isinstance(key, str):
        raise TypeError(f"theme attribute names must be strings; got {type(key).__name__}")
    if not _DOT_ID.fullmatch(key):
        raise ValueError(f"invalid Graphviz attribute name {key!r}")
    return key


def _validate_attr_value(value: object) -> str | int | float | bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"theme numeric attributes must be finite; got {value!r}")
        return value
    if isinstance(value, str):
        return value
    raise TypeError(
        "theme attribute values must be str, int, float, or bool; "
        f"got {type(value).__name__}"
    )


def _copy_attrs(attrs: Mapping[str, object] | None) -> MappingProxyType[str, AttributeValue]:
    if attrs is None:
        return MappingProxyType({})
    if not isinstance(attrs, Mapping):
        raise TypeError(f"theme attributes must be a mapping; got {type(attrs).__name__}")
    copied = {
        _validate_attr_key(key): _validate_attr_value(value)
        for key, value in attrs.items()
    }
    return MappingProxyType(copied)


def _merge_attrs(
    parent: Mapping[str, AttributeValue], child: Mapping[str, object] | None
) -> dict[str, object]:
    result = dict(parent)
    if child is not None:
        if not isinstance(child, Mapping):
            raise TypeError(f"theme attributes must be a mapping; got {type(child).__name__}")
        result.update(child)
    return result


def _copy_styles(
    styles: Mapping[str, Mapping[str, object]] | None, kind: str
) -> MappingProxyType[str, MappingProxyType[str, AttributeValue]]:
    if styles is None:
        return MappingProxyType({})
    if not isinstance(styles, Mapping):
        raise TypeError(f"theme {kind} styles must be a mapping; got {type(styles).__name__}")
    copied: dict[str, MappingProxyType[str, AttributeValue]] = {}
    for name, attrs in styles.items():
        if not isinstance(name, str):
            raise TypeError(
                f"theme {kind} style names must be strings; got {type(name).__name__}"
            )
        if not isinstance(attrs, Mapping):
            raise TypeError(
                f"theme {kind} style {name!r} must be a mapping; "
                f"got {type(attrs).__name__}"
            )
        copied[name] = _copy_attrs(attrs)
    return MappingProxyType(copied)


def _merge_styles(
    parent: Mapping[str, Mapping[str, AttributeValue]],
    child: Mapping[str, Mapping[str, object]] | None,
    kind: str,
) -> dict[str, dict[str, object]]:
    result = {name: dict(attrs) for name, attrs in parent.items()}
    if child is None:
        return result
    if not isinstance(child, Mapping):
        raise TypeError(f"theme {kind} styles must be a mapping; got {type(child).__name__}")
    for name, attrs in child.items():
        if not isinstance(name, str):
            raise TypeError(
                f"theme {kind} style names must be strings; got {type(name).__name__}"
            )
        if not isinstance(attrs, Mapping):
            raise TypeError(
                f"theme {kind} style {name!r} must be a mapping; "
                f"got {type(attrs).__name__}"
            )
        merged = result.setdefault(name, {})
        merged.update(attrs)
    return result


def _style_attrs(
    styles: Mapping[str, Mapping[str, AttributeValue]],
    kind: str,
    name: str,
    overrides: Mapping[str, object],
) -> dict[str, AttributeValue]:
    if not isinstance(name, str):
        raise TypeError(f"{kind} style name must be a string; got {type(name).__name__}")
    if name not in styles:
        available = ", ".join(repr(style_name) for style_name in styles)
        suffix = (
            f"; available styles: {available}"
            if available
            else "; no styles are defined"
        )
        raise KeyError(f"unknown {kind} style {name!r}{suffix}")
    result = dict(styles[name])
    result.update(_copy_attrs(overrides))
    return result


def _quote_string(value: str) -> str:
    """Quote a DOT string while preserving Graphviz escString sequences.

    Graphviz uses backslash escapes such as ``\\n`` and ``\\N`` in many string
    attributes.  Known escString sequences remain intact; other backslashes
    are doubled, and quotes are escaped for the DOT lexer.
    """
    output: list[str] = ['"']
    index = 0
    while index < len(value):
        char = value[index]
        if char == '"':
            output.append(r'\"')
        elif char == "\\":
            if index + 1 < len(value) and value[index + 1] == "\\":
                output.append(r"\\")
                index += 1
            elif index + 1 < len(value) and value[index + 1] in _ESCSTRING_ESCAPES:
                output.append("\\" + value[index + 1])
                index += 1
            else:
                output.append(r"\\")
        elif char == "\r":
            output.append(r"\r")
        elif char == "\n":
            output.append(r"\n")
        else:
            output.append(char)
        index += 1
    output.append('"')
    return "".join(output)


def _serialize_value(value: AttributeValue) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return _quote_string(str(value))


def _serialize_attrs(attrs: Mapping[str, AttributeValue]) -> str:
    return ", ".join(
        f"{_quote_string(key)}={_serialize_value(value)}"
        for key, value in attrs.items()
    )


def _skip_ignored(source: str, index: int) -> int:
    """Skip whitespace, comments, and preprocessor lines outside strings."""
    length = len(source)
    while index < length:
        if source[index].isspace():
            index += 1
            continue
        if source.startswith("//", index):
            newline = source.find("\n", index + 2)
            index = length if newline < 0 else newline + 1
            continue
        if source.startswith("/*", index):
            end = source.find("*/", index + 2)
            if end < 0:
                raise ValueError("malformed DOT: unterminated block comment")
            index = end + 2
            continue
        if source[index] == "#":
            newline = source.find("\n", index + 1)
            index = length if newline < 0 else newline + 1
            continue
        break
    return index


def _read_quoted(source: str, index: int) -> int:
    """Return the index after a DOT quoted string."""
    assert source[index] == '"'
    index += 1
    while index < len(source):
        if source[index] == "\\":
            index += 2
            continue
        if source[index] == '"':
            return index + 1
        index += 1
    raise ValueError("malformed DOT: unterminated quoted graph name")


def _read_html(source: str, index: int) -> int:
    """Return the index after a balanced DOT HTML ID."""
    assert source[index] == "<"
    depth = 0
    quote: str | None = None
    while index < len(source):
        char = source[index]
        if quote is not None:
            if char == "\\":
                index += 2
                continue
            if char == quote:
                quote = None
        elif char == '"':
            quote = char
        elif char == "<":
            depth += 1
        elif char == ">":
            depth -= 1
            if depth == 0:
                return index + 1
        index += 1
    raise ValueError("malformed DOT: unterminated HTML graph name")


def _read_id(source: str, index: int) -> int:
    start = index
    while index < len(source) and not source[index].isspace() and source[index] not in "{};[]()":
        if source.startswith("//", index) or source.startswith("/*", index):
            break
        index += 1
    if index == start:
        raise ValueError("malformed DOT: expected a graph name or opening brace")
    token = source[start:index]
    if not _DOT_ID.fullmatch(token):
        raise ValueError(f"malformed DOT: invalid graph header token {token!r}")
    return index


def _read_graph_name(source: str, index: int) -> int:
    """Read one DOT graph name, including quoted-string concatenation."""
    if source[index] == '"':
        index = _read_quoted(source, index)
        while True:
            next_index = _skip_ignored(source, index)
            if next_index >= len(source) or source[next_index] != "+":
                return next_index
            index = _skip_ignored(source, next_index + 1)
            if index >= len(source) or source[index] != '"':
                raise ValueError(
                    "malformed DOT: quoted graph name concatenation must use quoted strings"
                )
            index = _read_quoted(source, index)
    if source[index] == "<":
        return _read_html(source, index)
    return _read_id(source, index)


def _root_body_start(source: str) -> int:
    """Find the opening brace of a valid root DOT graph."""
    index = _skip_ignored(source, 0)
    if index >= len(source):
        raise ValueError("malformed DOT: expected a graph or digraph declaration")

    header_start = index
    while index < len(source) and _is_header_id_char(source[index]):
        index += 1
    keyword = source[header_start:index]
    keyword = keyword.lower()
    if keyword == "strict":
        index = _skip_ignored(source, index)
        graph_start = index
        while index < len(source) and _is_header_id_char(source[index]):
            index += 1
        keyword = source[graph_start:index].lower()
    if keyword not in {"graph", "digraph"}:
        raise ValueError("malformed DOT: expected graph, digraph, strict graph, or strict digraph")

    index = _skip_ignored(source, index)
    if index >= len(source):
        raise ValueError("malformed DOT: expected opening brace after graph declaration")
    if source[index] != "{":
        index = _read_graph_name(source, index)
        index = _skip_ignored(source, index)
    if index >= len(source) or source[index] != "{":
        raise ValueError("malformed DOT: expected opening brace after graph name")
    return index + 1


@dataclass(frozen=True, slots=True, init=False, eq=False)
class Theme:
    """Graphviz defaults that can be composed and applied to DOT source.

    Global ``graph``, ``node``, and ``edge`` mappings provide Graphviz defaults.
    ``nodes`` and ``edges`` hold generic named styles for callers building
    individual elements. Named lookups return only the selected style; global
    defaults remain the responsibility of ``theme=`` or explicit composition.
    """

    graph: Mapping[str, AttributeValue]
    node: Mapping[str, AttributeValue]
    edge: Mapping[str, AttributeValue]
    nodes: Mapping[str, Mapping[str, AttributeValue]]
    edges: Mapping[str, Mapping[str, AttributeValue]]

    def __init__(
        self,
        *,
        graph: Mapping[str, object] | None = None,
        node: Mapping[str, object] | None = None,
        edge: Mapping[str, object] | None = None,
        nodes: Mapping[str, Mapping[str, object]] | None = None,
        edges: Mapping[str, Mapping[str, object]] | None = None,
    ) -> None:
        object.__setattr__(self, "graph", _copy_attrs(graph))
        object.__setattr__(self, "node", _copy_attrs(node))
        object.__setattr__(self, "edge", _copy_attrs(edge))
        object.__setattr__(self, "nodes", _copy_styles(nodes, "node"))
        object.__setattr__(self, "edges", _copy_styles(edges, "edge"))

    def extend(
        self,
        *,
        graph: Mapping[str, object] | None = None,
        node: Mapping[str, object] | None = None,
        edge: Mapping[str, object] | None = None,
        nodes: Mapping[str, Mapping[str, object]] | None = None,
        edges: Mapping[str, Mapping[str, object]] | None = None,
    ) -> "Theme":
        """Return an independent theme with attribute-level overrides."""
        return Theme(
            graph=_merge_attrs(self.graph, graph),
            node=_merge_attrs(self.node, node),
            edge=_merge_attrs(self.edge, edge),
            nodes=_merge_styles(self.nodes, nodes, "node"),
            edges=_merge_styles(self.edges, edges, "edge"),
        )

    def node_attrs(self, name: str, **overrides: object) -> dict[str, AttributeValue]:
        """Return one named node style, optionally with per-element overrides."""
        return _style_attrs(self.nodes, "node", name, overrides)

    def edge_attrs(self, name: str, **overrides: object) -> dict[str, AttributeValue]:
        """Return one named edge style, optionally with per-element overrides."""
        return _style_attrs(self.edges, "edge", name, overrides)

    def apply(self, dot: str | DotSource) -> str:
        """Inject this theme's Graphviz defaults into DOT source."""
        source = _dot_text(dot)
        body_start = _root_body_start(source)
        if not (self.graph or self.node or self.edge):
            return source
        statements: list[str] = []
        for name, attrs in (("graph", self.graph), ("node", self.node), ("edge", self.edge)):
            if attrs:
                statements.append(f"  {name} [{_serialize_attrs(attrs)}];")
        injected = "\n" + "\n".join(statements) + "\n"
        return source[:body_start] + injected + source[body_start:]


__all__ = ["Theme"]
