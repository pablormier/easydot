"""Small, composable style presets for common graph domains.

The presets are ordinary :class:`easydot.Theme` instances. Named styles are
looked up explicitly with ``node_attrs()`` and ``edge_attrs()``; they do not
introduce a vocabulary parser or infer roles from DOT source.
"""

from easydot import Theme


biology = Theme(
    graph={"rankdir": "LR"},
    node={
        "shape": "ellipse",
        "style": "filled",
        "fillcolor": "#F8FAFC",
        "color": "#475569",
        "fontname": "Helvetica",
        "fontsize": 10,
    },
    edge={
        "color": "#64748B",
        "fontname": "Helvetica",
        "fontsize": 9,
        "arrowsize": 0.8,
    },
    nodes={
        "gene": {"shape": "box", "fillcolor": "#DBEAFE", "color": "#2563EB"},
        "rna": {"fillcolor": "#DCFCE7", "color": "#16A34A"},
        "protein": {"fillcolor": "#FEF3C7", "color": "#D97706"},
        "transcription_factor": {
            "shape": "hexagon",
            "fillcolor": "#FCE7F3",
            "color": "#DB2777",
        },
    },
    edges={
        "interaction": {"arrowhead": "none"},
        "activation": {"color": "#15803D", "arrowhead": "normal"},
        "inhibition": {"color": "#B91C1C", "arrowhead": "tee"},
    },
)


signaling = biology.extend(
    nodes={
        "receptor": {"shape": "diamond", "fillcolor": "#E0E7FF", "color": "#4F46E5"},
        "complex": {"shape": "octagon", "fillcolor": "#F3E8FF", "color": "#9333EA"},
        "small_molecule": {
            "shape": "circle",
            "fillcolor": "#E0F2FE",
            "color": "#0284C7",
        },
        "phenotype": {
            "shape": "doublecircle",
            "fillcolor": "#F3F4F6",
            "color": "#374151",
        },
    },
    edges={
        "phosphorylation": {
            "color": "#7C3AED",
            "style": "dashed",
            "arrowhead": "normal",
        },
    },
)


gene_regulation = biology.extend(
    nodes={"promoter": {"shape": "box3d", "fillcolor": "#FEF3C7", "color": "#A16207"}},
    edges={"transcription": {"color": "#0F766E", "arrowhead": "normal"}},
)


__all__ = ["biology", "signaling", "gene_regulation"]
