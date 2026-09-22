from __future__ import annotations

import math
import subprocess

import pytest

import easydot
from easydot import Theme


def test_theme_snapshots_inputs_and_extend_is_independent():
    graph = {"rankdir": "LR"}
    node = {"shape": "box"}
    theme = Theme(graph=graph, node=node)
    graph["rankdir"] = "TB"
    node["shape"] = "ellipse"

    derived = theme.extend(node={"color": "navy"})

    assert theme.graph == {"rankdir": "LR"}
    assert theme.node == {"shape": "box"}
    assert derived.node == {"shape": "box", "color": "navy"}
    assert derived.graph == theme.graph
    with pytest.raises(TypeError):
        theme.node["color"] = "red"


def test_theme_snapshots_named_styles_recursively_and_exposes_read_only_views():
    nodes = {"gene": {"shape": "box", "color": "blue"}}
    edges = {"activation": {"color": "green"}}
    theme = Theme(nodes=nodes, edges=edges)
    nodes["gene"]["shape"] = "ellipse"
    edges["activation"]["color"] = "red"
    nodes["new"] = {"shape": "diamond"}

    assert theme.nodes["gene"] == {"shape": "box", "color": "blue"}
    assert theme.edges["activation"] == {"color": "green"}
    with pytest.raises(TypeError):
        theme.nodes["gene"] = {"shape": "ellipse"}
    with pytest.raises(TypeError):
        theme.nodes["gene"]["shape"] = "ellipse"
    with pytest.raises(TypeError):
        theme.edges["activation"]["color"] = "red"


def test_theme_cannot_reassign_validated_mappings():
    theme = Theme(graph={"rankdir": "LR"}, node={"shape": "box"})

    with pytest.raises(AttributeError):
        theme.graph = {}
    with pytest.raises(AttributeError):
        theme.node = {}
    with pytest.raises(AttributeError):
        theme.nodes = {}


def test_named_style_lookup_returns_only_style_delta_and_fresh_dicts():
    theme = Theme(
        node={"shape": "ellipse", "color": "gray"},
        edge={"color": "black"},
        nodes={"gene": {"shape": "box", "fillcolor": "blue"}},
        edges={"activation": {"color": "green", "arrowhead": "normal"}},
    )

    node_attrs = theme.node_attrs("gene", label="TP53")
    edge_attrs = theme.edge_attrs("activation", penwidth=2)
    assert node_attrs == {"shape": "box", "fillcolor": "blue", "label": "TP53"}
    assert edge_attrs == {"color": "green", "arrowhead": "normal", "penwidth": 2}
    assert "color" not in node_attrs
    assert theme.node_attrs("gene") is not node_attrs
    node_attrs["shape"] = "diamond"
    assert theme.node_attrs("gene")["shape"] == "box"
    assert dict(theme.node) | theme.node_attrs("gene") == {
        "shape": "box",
        "color": "gray",
        "fillcolor": "blue",
    }


def test_named_style_lookup_validates_overrides_and_unknown_names():
    theme = Theme(nodes={"gene": {"shape": "box"}}, edges={"activation": {}})
    with pytest.raises(TypeError, match="str, int, float, or bool"):
        theme.node_attrs("gene", label=object())
    with pytest.raises(ValueError, match="invalid Graphviz attribute name"):
        Theme(nodes={"gene": {"not a key": "x"}})
    with pytest.raises(TypeError, match="style 'gene' must be a mapping"):
        Theme(nodes={"gene": None})
    with pytest.raises(KeyError, match="unknown node style.*gene"):
        theme.node_attrs("protein")
    with pytest.raises(KeyError, match="unknown edge style.*activation"):
        theme.edge_attrs("binding")


def test_extend_inherits_and_merges_named_styles_without_mutating_parent():
    base = Theme(
        nodes={"protein": {"shape": "ellipse", "color": "blue"}},
        edges={"activation": {"color": "green", "arrowhead": "normal"}},
    )
    child = base.extend(
        nodes={"protein": {"color": "lime"}, "gene": {"shape": "box"}},
        edges={"activation": {"penwidth": 2}, "inhibition": {"arrowhead": "tee"}},
    )

    assert base.node_attrs("protein") == {"shape": "ellipse", "color": "blue"}
    assert base.edge_attrs("activation") == {"color": "green", "arrowhead": "normal"}
    assert child.node_attrs("protein") == {"shape": "ellipse", "color": "lime"}
    assert child.node_attrs("gene") == {"shape": "box"}
    assert child.edge_attrs("activation") == {
        "color": "green",
        "arrowhead": "normal",
        "penwidth": 2,
    }
    assert child.edge_attrs("inhibition") == {"arrowhead": "tee"}


def test_explicit_named_style_attrs_combine_with_theme_defaults(monkeypatch):
    seen = []

    def fake_native(dot, *, engine, format):
        seen.append(dot)
        return "<svg />"

    monkeypatch.setattr(easydot._native_module, "native", fake_native)
    theme = Theme(
        node={"color": "gray"},
        nodes={"gene": {"shape": "box", "fillcolor": "blue"}},
    )
    attrs = theme.node_attrs("gene")
    dot = f'digraph {{ A [shape="{attrs["shape"]}", fillcolor="{attrs["fillcolor"]}"] }}'
    easydot.plot(dot, backend="native", theme=theme)
    assert seen[0].count('node ["color"="gray"];') == 1
    assert seen[0].count('shape="box"') == 1
    assert seen[0].count('fillcolor="blue"') == 1


def test_theme_empty_sections_are_not_injected():
    source = "digraph { A -> B }"
    assert Theme().apply(source) == source


@pytest.mark.parametrize(
    "source",
    [
        "graph { A -- B }",
        "digraph { A -> B }",
        "strict graph { A -- B }",
        "strict digraph { A -> B }",
        "Graph { A -- B }",
        "DiGraph { A -> B }",
        "STRICT GRAPH { A -- B }",
        "STRICT DIGRAPH G { A -> B }",
        'digraph example { A -> B }',
        'digraph "name with { braces }" { A -> B }',
        'digraph -1 { A -> B }',
        'digraph <b> { A -> B }',
        'digraph <<b>foo</b>> { A -> B }',
        'digraph "foo" + "bar" { A -> B }',
    ],
)
def test_theme_inserts_inside_root_graph(source):
    result = Theme(node={"shape": "box"}).apply(source)
    statement = 'node ["shape"="box"];'
    statement_index = result.index(statement)
    body_node_index = result.rindex("A")
    root_brace_index = result.rfind("{", 0, body_node_index)
    assert statement_index > root_brace_index
    assert result[statement_index - 3 : statement_index] == "\n  "
    assert statement_index < body_node_index


def test_theme_ignores_comments_and_preprocessor_lines():
    source = """#line 1
// fake { brace
/* another { fake brace */
strict digraph /* header comment */ "g{raph" {
  A -> B
}
"""
    result = Theme(graph={"rankdir": "LR"}).apply(source)
    assert result.count('graph ["rankdir"="LR"];') == 1
    assert result.index('graph ["rankdir"="LR"];') > result.index('"g{raph" {')


@pytest.mark.parametrize(
    "source",
    ["digraph <b { A -> B }", 'digraph "unterminated + "bar" { A -> B }'],
)
def test_theme_rejects_malformed_graph_names(source):
    with pytest.raises(ValueError, match="malformed DOT"):
        Theme(node={"shape": "box"}).apply(source)


@pytest.mark.parametrize(
    "source",
    ["", "A -> B", "digraph", "digraph name", 'digraph "unterminated {'],
)
def test_theme_rejects_malformed_dot(source):
    with pytest.raises(ValueError, match="malformed DOT"):
        Theme(node={"shape": "box"}).apply(source)


def test_theme_serializes_values_and_graphviz_escapes():
    result = Theme(
        graph={"rankdir": "LR", "splines": True},
        node={
            "label": r"line\n\N",
            "tooltip": 'say "hello"',
            "width": 1.25,
            "count": 2,
            "fixedsize": False,
        },
    ).apply("digraph { A }")
    assert 'graph ["rankdir"="LR", "splines"=true];' in result
    assert '"label"="line\\n\\N"' in result
    assert '"tooltip"="say \\\"hello\\\""' in result
    assert '"width"="1.25"' in result
    assert '"count"="2"' in result
    assert '"fixedsize"=false' in result


def test_theme_quotes_scientific_values_and_keyword_attribute_names():
    result = Theme(node={"width": 1e-5, "graph": "x"}).apply("digraph { A }")
    assert 'node ["width"="1e-05", "graph"="x"];' in result


@pytest.mark.parametrize("escape", list("NGETHLnlr"))
def test_theme_preserves_graphviz_escstring_backslash_substitutions(escape):
    one = Theme(node={"label": "\\" + escape}).apply("digraph { A }")
    two = Theme(node={"label": "\\\\" + escape}).apply("digraph { A }")

    assert f'"label"="\\{escape}"' in one
    assert f'"label"="\\\\{escape}"' in two
    assert one.count("\\") == 1
    assert two.count("\\") == 2


@pytest.mark.parametrize("value", [math.inf, -math.inf, math.nan])
def test_theme_rejects_non_finite_numeric_values(value):
    with pytest.raises(ValueError, match="finite"):
        Theme(node={"width": value})


def test_theme_rejects_unsupported_values_and_invalid_keys():
    with pytest.raises(TypeError, match="str, int, float, or bool"):
        Theme(node={"shape": object()})
    with pytest.raises(ValueError, match="invalid Graphviz attribute name"):
        Theme(node={"not a key": "box"})


def test_theme_accepts_to_string_sources():
    class Source:
        def to_string(self) -> str:
            return "digraph { A -> B }"

    assert 'node ["shape"="box"];' in Theme(node={"shape": "box"}).apply(Source())


def test_theme_defaults_precede_user_defaults_and_element_attributes():
    source = "digraph { node [shape=diamond]; A [shape=hexagon]; A -> B [color=red] }"
    result = Theme(
        node={"shape": "box", "color": "navy"}, edge={"color": "gray"}
    ).apply(source)
    assert result.index('node ["shape"="box", "color"="navy"];') < result.index(
        "node [shape=diamond]"
    )
    assert result.index("node [shape=diamond]") < result.index("A [shape=hexagon]")
    assert result.index('edge ["color"="gray"];') < result.index("A -> B [color=red]")


def test_theme_is_integrated_once_for_graph_and_rich_representations(monkeypatch):
    calls = []

    def fake_browser(dot, **kwargs):
        calls.append(dot)
        return dot

    monkeypatch.setattr(easydot, "_browser_html", fake_browser)
    theme = Theme(node={"shape": "box"})
    graph = easydot.render("digraph { A -> B }", backend="browser", theme=theme)

    assert graph.dot == "digraph { A -> B }"
    assert graph.theme is theme
    graph._body_html()
    graph._body_html()
    assert calls == [graph._effective_dot, graph._effective_dot]
    assert graph._effective_dot.count('node ["shape"="box"];') == 1


def test_theme_is_passed_to_all_static_entry_points(monkeypatch):
    seen = []

    def fake_native(dot, *, engine, format):
        seen.append(dot)
        return "<svg />" if format == "svg" else b"png"

    monkeypatch.setattr(easydot._native_module, "native", fake_native)
    theme = Theme(node={"shape": "box"})
    easydot.svg("digraph { A }", backend="native", theme=theme)
    easydot.plot("digraph { A }", backend="native", theme=theme)
    easydot.html("digraph { A }", backend="native", theme=theme)
    assert all(dot.count('node ["shape"="box"];') == 1 for dot in seen)


def test_theme_native_direct_entry_point(monkeypatch):
    seen = []

    def fake_run(args, *, input, stdout, stderr, check):
        seen.append(input.decode())
        return subprocess.CompletedProcess(args, 0, b"ok", b"")

    monkeypatch.setattr(easydot._native_module.subprocess, "run", fake_run)
    easydot.native("digraph { A }", format="plain", theme=Theme(node={"shape": "box"}))
    assert seen[0].count('node ["shape"="box"];') == 1


def test_public_wasm_entry_points_receive_prepared_dot_once(monkeypatch):
    seen = []

    def fake_render(dot, *, format, engine):
        seen.append(dot)
        return "<svg />" if format == "svg" else b"png"

    def fake_svg(dot, *, engine):
        seen.append(dot)
        return "<svg />"

    monkeypatch.setattr(easydot._wasm_module, "render", fake_render)
    monkeypatch.setattr(easydot._wasm_module, "svg", fake_svg)
    theme = Theme(node={"shape": "box"})

    assert easydot.svg("digraph { A }", backend="wasm", theme=theme) == "<svg />"
    assert easydot.plot("digraph { A }", backend="wasm", theme=theme).data == "<svg />"
    assert easydot.html("digraph { A }", backend="wasm", theme=theme)
    assert all(dot.count('node ["shape"="box"];') == 1 for dot in seen)


def test_theme_serialization_smoke_with_wasi_graphviz():
    wasi_graphviz = pytest.importorskip("wasi_graphviz")
    dot = Theme(node={"width": 1e-5, "graph": "x"}).apply("digraph { A }")
    rendered = wasi_graphviz.render(dot, format="svg", engine="dot")
    assert b"<svg" in rendered


@pytest.mark.parametrize(
    "source",
    [
        "digraph <don't> { A }",
        'digraph <b title="quoted text"> { A }',
        'digraph <"quoted"> { A }',
    ],
)
def test_theme_accepts_graphviz_html_graph_names(source):
    wasi_graphviz = pytest.importorskip("wasi_graphviz")
    dot = Theme(node={"shape": "box"}).apply(source)
    assert b"<svg" in wasi_graphviz.render(dot, format="svg", engine="dot")
