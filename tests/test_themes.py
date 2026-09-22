from __future__ import annotations

import pytest

from easydot import Theme
from easydot.themes import biology, gene_regulation, signaling


def test_preset_vocabularies_are_small_and_documented():
    assert {"gene", "rna", "protein", "transcription_factor"} <= set(biology.nodes)
    assert {"interaction", "activation", "inhibition"} <= set(biology.edges)
    assert {"receptor", "complex", "small_molecule", "phenotype"} == (
        set(signaling.nodes) - set(biology.nodes)
    )
    assert {"phosphorylation"} == set(signaling.edges) - set(biology.edges)
    assert {"promoter"} <= set(gene_regulation.nodes) - set(biology.nodes)
    assert {"transcription"} <= set(gene_regulation.edges) - set(biology.edges)


def test_specialized_presets_inherit_biology_styles():
    assert signaling.node_attrs("gene") == biology.node_attrs("gene")
    assert signaling.edge_attrs("activation") == biology.edge_attrs("activation")
    assert signaling.node_attrs("small_molecule")["shape"] == "circle"
    assert signaling.node_attrs("phenotype")["shape"] == "doublecircle"
    assert gene_regulation.node_attrs("protein") == biology.node_attrs("protein")
    assert gene_regulation.edge_attrs("inhibition") == biology.edge_attrs("inhibition")


def test_extending_a_preset_does_not_mutate_original():
    custom = biology.extend(
        node={"fontname": "DejaVu Sans"},
        nodes={"gene": {"fillcolor": "white"}, "metabolite": {"shape": "circle"}},
        edges={"conversion": {"arrowhead": "normal"}},
    )

    assert custom.node["fontname"] == "DejaVu Sans"
    assert biology.node["fontname"] == "Helvetica"
    assert custom.node_attrs("gene")["fillcolor"] == "white"
    assert biology.node_attrs("gene")["fillcolor"] == "#DBEAFE"
    assert "metabolite" not in biology.nodes
    assert "conversion" not in biology.edges


def test_preset_lookup_overrides_are_named_style_deltas():
    attrs = signaling.node_attrs("receptor", label="EGFR")

    assert attrs["label"] == "EGFR"
    assert attrs["shape"] == "diamond"
    assert attrs["fillcolor"] == "#E0E7FF"
    assert attrs["color"] == "#4F46E5"
    assert "fontname" not in attrs
    assert "style" not in attrs


def test_signaling_preset_renders_without_pydot():
    wasi_graphviz = pytest.importorskip("wasi_graphviz")
    for role in ("small_molecule", "phenotype"):
        attrs = signaling.node_attrs(role)
        dot = Theme(node=attrs).apply("digraph { A }")
        rendered = wasi_graphviz.render(dot, format="svg", engine="dot")

        assert f'"shape"="{attrs["shape"]}"' in dot
        assert rendered.startswith(b"<?xml") or b"<svg" in rendered
