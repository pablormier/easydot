"""SVG glyph validation and placement over Graphviz proxy shapes."""

from __future__ import annotations

import base64
import math
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree as ET


_SVG_NS = "http://www.w3.org/2000/svg"
_XLINK_NS = "http://www.w3.org/1999/xlink"
_NUMBER_RE = re.compile(r"[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?")
_CSS_URL_RE = re.compile(r"url\(\s*(?:(['\"])(.*?)\1|([^)]*?))\s*\)", re.IGNORECASE | re.DOTALL)
_CSS_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)
_ACTIVE_ELEMENTS = frozenset(
    {
        "script",
        "foreignobject",
        "animate",
        "animatemotion",
        "animatetransform",
        "set",
        "discard",
        "audio",
        "video",
        "iframe",
        "object",
        "embed",
    }
)


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _self_contained_reference(value: str) -> bool:
    value = value.strip()
    if not value or value.startswith("#"):
        return True
    if not value.lower().startswith("data:"):
        return False
    media_type = value[5:].split(";", 1)[0].split(",", 1)[0].lower()
    return media_type.startswith(("image/", "font/")) or media_type in {
        "application/font-woff",
        "application/vnd.ms-fontobject",
        "application/x-font-ttf",
        "application/x-font-opentype",
    }


def _validate_reference(value: str) -> None:
    if not _self_contained_reference(value):
        raise ValueError("SVG glyphs must be self-contained; external references are unsupported")


def _validate_css_urls(value: str) -> None:
    css = _CSS_COMMENT_RE.sub("", value)
    if "\\" in css and "(" in css:
        raise ValueError("SVG glyph CSS escapes are unsupported")
    if re.search(r"@import\b", css, re.IGNORECASE):
        raise ValueError("SVG glyphs must be self-contained; CSS imports are unsupported")
    for match in _CSS_URL_RE.finditer(css):
        url = match.group(2) if match.group(1) else match.group(3)
        if not _self_contained_reference(url or ""):
            raise ValueError(
                "SVG glyphs must be self-contained; external references are unsupported"
            )


def _validate_svg(svg: str) -> None:
    if not isinstance(svg, str):
        raise TypeError("SVG glyph content must be a string")
    try:
        root = ET.fromstring(svg)
    except ET.ParseError as exc:
        raise ValueError(f"invalid SVG glyph: {exc}") from exc
    if _local_name(root.tag) != "svg":
        raise ValueError("SVG glyph content must have an <svg> root element")
    if re.search(r"<!DOCTYPE\b", svg, re.IGNORECASE):
        raise ValueError("SVG glyphs must not include a DOCTYPE declaration")
    if re.search(r"<\?xml-stylesheet\b", svg, re.IGNORECASE):
        raise ValueError("SVG glyphs must be self-contained; external stylesheets are unsupported")

    for element in root.iter():
        if _local_name(element.tag).lower() in _ACTIVE_ELEMENTS:
            raise ValueError("SVG glyphs cannot include scripts, event handlers, or active content")
        for attribute, value in element.attrib.items():
            name = _local_name(attribute).lower()
            if name.startswith("on"):
                raise ValueError("SVG glyphs cannot include scripts, event handlers, or active content")
            if name in {"href", "src"}:
                _validate_reference(value)
            _validate_css_urls(value)
        if _local_name(element.tag).lower() == "style" and element.text:
            _validate_css_urls(element.text)


@dataclass(frozen=True, slots=True)
class SvgGlyph:
    """A self-contained SVG asset to place over a Graphviz proxy node.

    Create glyphs with :meth:`from_file` or :meth:`from_string`. The SVG is
    scaled to the exact bounds of the proxy ellipse or rectangular box.
    """

    svg: str

    def __post_init__(self) -> None:
        _validate_svg(self.svg)

    @classmethod
    def from_file(cls, path: str | Path) -> "SvgGlyph":
        """Read and validate an SVG glyph from a file."""
        return cls(Path(path).read_text(encoding="utf-8"))

    @classmethod
    def from_string(cls, svg: str) -> "SvgGlyph":
        """Validate SVG text and create a glyph."""
        return cls(svg)

    @property
    def _data_uri(self) -> str:
        encoded = base64.b64encode(self.svg.encode("utf-8")).decode("ascii")
        return f"data:image/svg+xml;base64,{encoded}"


def normalize_glyphs(
    glyphs: Mapping[str, SvgGlyph] | None,
) -> dict[str, SvgGlyph]:
    """Validate a node-ID-to-glyph mapping and return a plain dictionary."""
    if glyphs is None:
        return {}
    if not isinstance(glyphs, Mapping):
        raise TypeError("glyphs must be a mapping of DOT node ids to SvgGlyph values")
    result: dict[str, SvgGlyph] = {}
    for node_id, glyph in glyphs.items():
        if not isinstance(node_id, str) or not node_id:
            raise TypeError("glyphs mapping keys must be non-empty node id strings")
        if not isinstance(glyph, SvgGlyph):
            raise TypeError(f"glyphs[{node_id!r}] must be an SvgGlyph")
        result[node_id] = glyph
    return result


def _number(value: str, attribute: str, node_id: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"unsupported proxy geometry for node id {node_id!r}: invalid {attribute}"
        ) from exc
    if not math.isfinite(number):
        raise ValueError(
            f"unsupported proxy geometry for node id {node_id!r}: invalid {attribute}"
        )
    return number


def _polygon_bounds(points: str, node_id: str) -> tuple[float, float, float, float]:
    values = [float(value) for value in _NUMBER_RE.findall(points)]
    if len(values) < 8 or len(values) % 2:
        raise ValueError(
            f"unsupported proxy geometry for node id {node_id!r}: expected a rectangular box"
        )
    vertices = list(zip(values[::2], values[1::2], strict=True))
    if len(vertices) > 1 and vertices[0] == vertices[-1]:
        vertices.pop()
    unique = set(vertices)
    min_x = min(x for x, _ in unique)
    max_x = max(x for x, _ in unique)
    min_y = min(y for _, y in unique)
    max_y = max(y for _, y in unique)
    corners = {
        (min_x, min_y),
        (min_x, max_y),
        (max_x, min_y),
        (max_x, max_y),
    }
    if len(unique) != 4 or unique != corners or min_x == max_x or min_y == max_y:
        raise ValueError(
            f"unsupported proxy geometry for node id {node_id!r}: expected a rectangular box"
        )
    return min_x, min_y, max_x - min_x, max_y - min_y


def _shape_bounds(node: ET.Element, node_id: str) -> tuple[ET.Element, float, float, float, float]:
    for child in node:
        tag = _local_name(child.tag)
        if tag == "ellipse":
            cx = _number(child.get("cx", ""), "cx", node_id)
            cy = _number(child.get("cy", ""), "cy", node_id)
            rx = _number(child.get("rx", ""), "rx", node_id)
            ry = _number(child.get("ry", ""), "ry", node_id)
            if rx <= 0 or ry <= 0:
                break
            return child, cx - rx, cy - ry, rx * 2, ry * 2
        if tag == "polygon":
            return (child, *_polygon_bounds(child.get("points", ""), node_id))
    raise ValueError(
        f"unsupported proxy geometry for node id {node_id!r}: use shape=ellipse or shape=box"
    )


def compose_svg_glyphs(svg: str, glyphs: Mapping[str, SvgGlyph]) -> str:
    """Place glyph SVGs over corresponding Graphviz ellipse/box proxy nodes."""
    if not glyphs:
        return svg

    ET.register_namespace("", _SVG_NS)
    ET.register_namespace("xlink", _XLINK_NS)
    try:
        root = ET.fromstring(svg)
    except ET.ParseError as exc:
        raise ValueError(f"Graphviz returned invalid SVG: {exc}") from exc

    for node_id, glyph in glyphs.items():
        matches = [
            element
            for element in root.iter()
            if _local_name(element.tag) == "g"
            and "node" in element.get("class", "").split()
            and element.get("id") == node_id
        ]
        if not matches:
            raise ValueError(f"no Graphviz node with id {node_id!r} was found")
        if len(matches) > 1:
            raise ValueError(f"multiple Graphviz nodes have id {node_id!r}")

        node = matches[0]
        shape, x, y, width, height = _shape_bounds(node, node_id)
        image = ET.Element(f"{{{_SVG_NS}}}image")
        image.set("x", f"{x:g}")
        image.set("y", f"{y:g}")
        image.set("width", f"{width:g}")
        image.set("height", f"{height:g}")
        image.set("preserveAspectRatio", "none")
        image.set("href", glyph._data_uri)
        image.set(f"{{{_XLINK_NS}}}href", glyph._data_uri)
        node.insert(list(node).index(shape) + 1, image)

    return ET.tostring(root, encoding="unicode")
