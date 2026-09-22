from __future__ import annotations

import base64
from xml.etree import ElementTree as ET

import pytest

import easydot
from easydot import _glyphs
from easydot import _wasm


ELLIPSE_DOT = '''digraph {
  cell [id="cell-glyph", shape=ellipse, fixedsize=true,
        width=1, height=.8, label="", color=transparent]
  cell -> next
}'''
BOX_DOT = '''digraph {
  molecule [id="molecule-glyph", shape=box, fixedsize=true,
            width=1, height=.8, label="", color=transparent]
}'''
GLYPH_SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 80"><path d="M0 40h100"/></svg>'


def _svg_image(svg_text: str) -> ET.Element:
    root = ET.fromstring(svg_text)
    images = [element for element in root.iter() if element.tag.endswith("}image")]
    assert len(images) == 1
    return images[0]


def _graphviz_wasm_svg(dot: str) -> str:
    rendered = _wasm.render(dot, format="svg")
    assert isinstance(rendered, str)
    return rendered


def test_svg_glyph_from_string_and_file(tmp_path):
    path = tmp_path / "glyph.svg"
    path.write_text(GLYPH_SVG, encoding="utf-8")

    assert easydot.SvgGlyph.from_string(GLYPH_SVG).svg == GLYPH_SVG
    assert easydot.SvgGlyph.from_file(path).svg == GLYPH_SVG


@pytest.mark.parametrize("svg_text", ["not svg", "<html/>", "<svg>"])
def test_svg_glyph_rejects_invalid_content(svg_text):
    with pytest.raises(ValueError, match="SVG glyph"):
        easydot.SvgGlyph.from_string(svg_text)


@pytest.mark.parametrize(
    "svg_text",
    [
        '<svg xmlns="http://www.w3.org/2000/svg"><image href="https://example.org/a.png"/></svg>',
        '<svg xmlns="http://www.w3.org/2000/svg"><image href="../a.png"/></svg>',
        '<svg xmlns="http://www.w3.org/2000/svg"><rect style="fill:url(https://example.org/a.svg#shape)"/></svg>',
        '<svg xmlns="http://www.w3.org/2000/svg"><rect fill="u&#92;72l(https://example.org/a.svg#shape)"/></svg>',
        '<svg xmlns="http://www.w3.org/2000/svg"><style>.x{fill:url(//example.org/a.svg)}</style><rect class="x"/></svg>',
        '<svg xmlns="http://www.w3.org/2000/svg"><style>@import url(https://example.org/a.css);</style></svg>',
    ],
)
def test_svg_glyph_rejects_external_references(svg_text):
    with pytest.raises(ValueError, match="self-contained|external references|CSS escapes"):
        easydot.SvgGlyph.from_string(svg_text)


@pytest.mark.parametrize(
    "svg_text",
    [
        '<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>',
        '<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)"/>',
        '<svg xmlns="http://www.w3.org/2000/svg"><foreignObject><p>active</p></foreignObject></svg>',
        '<svg xmlns="http://www.w3.org/2000/svg"><animate attributeName="x"/></svg>',
    ],
)
def test_svg_glyph_rejects_active_content(svg_text):
    with pytest.raises(ValueError, match="active content"):
        easydot.SvgGlyph.from_string(svg_text)


def test_svg_glyph_allows_local_and_embedded_image_references():
    svg_text = '''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
      <defs><linearGradient id="g"/></defs>
      <rect fill="url(#g)"/>
      <image xlink:href="data:image/png;base64,AA=="/>
    </svg>'''

    assert easydot.SvgGlyph.from_string(svg_text).svg == svg_text


def test_compose_ellipse_glyph_matches_proxy_bounds():
    glyph = easydot.SvgGlyph.from_string(GLYPH_SVG)
    original = _graphviz_wasm_svg(ELLIPSE_DOT)
    composed = easydot.svg(ELLIPSE_DOT, backend="wasm", glyphs={"cell-glyph": glyph})
    image = _svg_image(composed)
    root = ET.fromstring(original)
    composed_root = ET.fromstring(composed)
    ellipse = next(element for element in root.iter() if element.tag.endswith("}ellipse"))

    assert float(image.get("x")) == pytest.approx(float(ellipse.get("cx")) - float(ellipse.get("rx")))
    assert float(image.get("y")) == pytest.approx(float(ellipse.get("cy")) - float(ellipse.get("ry")))
    assert float(image.get("width")) == pytest.approx(2 * float(ellipse.get("rx")))
    assert float(image.get("height")) == pytest.approx(2 * float(ellipse.get("ry")))
    assert image.get("preserveAspectRatio") == "none"
    assert image.get("href", "").startswith("data:image/svg+xml;base64,")
    embedded = base64.b64decode(image.get("href").split(",", 1)[1]).decode("utf-8")
    assert embedded == GLYPH_SVG
    original_paths = [element.get("d") for element in root.iter() if element.tag.endswith("}path")]
    composed_paths = [
        element.get("d") for element in composed_root.iter() if element.tag.endswith("}path")
    ]
    assert composed_paths == original_paths


def test_compose_box_glyph_matches_rectangular_proxy_bounds():
    glyph = easydot.SvgGlyph.from_string(GLYPH_SVG)
    original = ET.fromstring(_graphviz_wasm_svg(BOX_DOT))
    composed = ET.fromstring(
        easydot.svg(BOX_DOT, backend="wasm", glyphs={"molecule-glyph": glyph})
    )
    node = next(element for element in original.iter() if element.get("id") == "molecule-glyph")
    polygon = next(element for element in node if element.tag.endswith("}polygon"))
    numbers = [float(item) for item in _glyphs._NUMBER_RE.findall(polygon.get("points"))]
    xs, ys = numbers[::2], numbers[1::2]
    image = next(element for element in composed.iter() if element.tag.endswith("}image"))

    assert float(image.get("x")) == min(xs)
    assert float(image.get("y")) == min(ys)
    assert float(image.get("width")) == max(xs) - min(xs)
    assert float(image.get("height")) == max(ys) - min(ys)


def test_missing_and_unsupported_proxy_nodes_fail_clearly():
    glyph = easydot.SvgGlyph.from_string(GLYPH_SVG)
    with pytest.raises(ValueError, match="no Graphviz node"):
        easydot.svg("digraph { A }", backend="wasm", glyphs={"absent": glyph})

    diamond = 'digraph { A [id="glyph", shape=diamond, label=""] }'
    with pytest.raises(ValueError, match="unsupported proxy geometry"):
        easydot.svg(diamond, backend="wasm", glyphs={"glyph": glyph})


def test_duplicate_node_ids_fail_clearly():
    dot = 'digraph { A [id="same", label=""]; B [id="same", label=""] }'
    with pytest.raises(ValueError, match="multiple Graphviz nodes"):
        easydot.svg(dot, backend="wasm", glyphs={"same": easydot.SvgGlyph(GLYPH_SVG)})


def test_html_and_plot_include_glyphs_for_static_backends():
    glyph = easydot.SvgGlyph(GLYPH_SVG)
    rendered = easydot.html(ELLIPSE_DOT, backend="wasm", glyphs={"cell-glyph": glyph})
    plotted = easydot.plot(ELLIPSE_DOT, backend="wasm", glyphs={"cell-glyph": glyph})

    assert "data:image/svg+xml;base64," in rendered
    assert isinstance(plotted.data, str)
    assert "<image" in plotted.data


def test_graph_uses_glyph_for_browser_html_and_static_repr():
    glyph = easydot.SvgGlyph(GLYPH_SVG)
    browser_graph = easydot.render(
        ELLIPSE_DOT,
        backend="browser",
        source="cdn",
        glyphs={"cell-glyph": glyph},
    )
    browser_html = browser_graph._body_html()
    assert "composeSvgGlyphs" in browser_html
    assert "__EASYDOT_GLYPHS__" not in browser_html
    assert "image/svg+xml;base64," in browser_html

    static_graph = easydot.render(ELLIPSE_DOT, backend="wasm", glyphs={"cell-glyph": glyph})
    assert "<image" in static_graph._repr_svg_()


def test_browser_composes_after_worker_or_main_thread_layout():
    rendered = easydot.html(
        ELLIPSE_DOT,
        backend="browser",
        source="cdn",
        worker=True,
        glyphs={"cell-glyph": easydot.SvgGlyph(GLYPH_SVG)},
    )

    assert "const svg = graphviz.layout(dot, format, engine)" in rendered
    assert "svg = composeSvgGlyphs(svg, glyphs)" in rendered
    assert rendered.index("svg = composeSvgGlyphs(svg, glyphs)") < rendered.index(
        "target.insertAdjacentHTML('beforeend', svg)"
    )


def test_png_rejects_nonempty_glyph_mapping():
    with pytest.raises(ValueError, match="SVG glyphs require format='svg'"):
        easydot.plot(
            ELLIPSE_DOT,
            format="png",
            backend="wasm",
            glyphs={"cell-glyph": easydot.SvgGlyph(GLYPH_SVG)},
        )


def test_no_glyph_mapping_preserves_original_svg(monkeypatch):
    original = _graphviz_wasm_svg(ELLIPSE_DOT)
    monkeypatch.setattr(_wasm, "svg", lambda dot, engine="dot": original)

    assert easydot.svg(ELLIPSE_DOT, backend="wasm") == original
