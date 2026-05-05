# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "easydot==0.2.2",
#     "marimo>=0.23.5",
# ]
# ///

import marimo

__generated_with = "0.23.4"
app = marimo.App(width="medium")


@app.cell
def _():
    import easydot
    import marimo as mo

    def dot(dot_source: str, **kwargs):
        return easydot.render(
            dot_source,
            backend="browser",
            source="cdn",
            iframe_mode="srcdoc",
            fit=kwargs.pop("fit", "horizontal"),
            **kwargs,
        )

    return dot, easydot, mo


@app.cell
def _(mo):
    mo.md(r"""
    <p align="center">
      <img
        src="https://raw.githubusercontent.com/pablormier/easydot/main/assets/easydot-logo.png"
        alt="easydot"
        width="260"
      />
    </p>

    # Graphviz diagrams in marimo with easydot

    [`easydot`](https://github.com/pablormier/easydot) lets a Python notebook render the
    [DOT language](https://graphviz.org/doc/info/lang.html) directly in
    the browser. You write a small text description of a graph;
    [Graphviz](https://graphviz.org/) computes the layout; `easydot`
    displays the result as a crisp SVG.

    DOT is a good fit for public notebooks because it is plain text,
    readable in diffs, easy to generate from Python, and expressive enough
    for flow charts, system diagrams, dependency graphs, state machines,
    and networks.
    """)
    return


@app.cell
def _():
    first_dot = """
    digraph {
      graph [rankdir=LR, bgcolor="transparent", pad=0.2];
      node [
        shape=box,
        style="rounded,filled",
        fontname="Helvetica",
        margin="0.16,0.10",
        color="#334155",
        fillcolor="#f8fafc"
      ];
      edge [fontname="Helvetica", color="#64748b", arrowsize=0.8];

      idea [label="Idea"];
      dot [label="DOT text"];
      graphviz [label="Graphviz layout"];
      svg [label="SVG in marimo"];

      idea -> dot -> graphviz -> svg;
    }
    """
    return (first_dot,)


@app.cell
def _(dot, first_dot, mo):
    mo.vstack(
        [
            mo.md("## 1. Start with a tiny DOT graph"),
            mo.hstack(
                [
                    mo.vstack(
                        [
                            mo.md("DOT describes the relationships and styling."),
                            mo.md(f"```dot\n{first_dot}\n```"),
                        ]
                    ),
                    mo.vstack(
                        [
                            mo.md("Graphviz chooses the geometry; easydot displays it."),
                            dot(first_dot),
                        ]
                    ),
                ],
                wrap=True,
                gap=2,
            ),
        ]
    )
    return


@app.cell
def _():
    style_dot = """
    digraph {
      graph [
        rankdir=LR,
        bgcolor="transparent",
        pad=0.20,
        nodesep=0.48,
        ranksep=0.85
      ];
      node [
        shape=box,
        style="rounded,filled",
        fontname="Helvetica",
        fontsize=12,
        margin="0.16,0.10",
        color="#334155",
        fillcolor="#f8fafc"
      ];
      edge [fontname="Helvetica", fontsize=10, color="#64748b", arrowsize=0.75];

      collect [label="Collect data", fillcolor="#e0f2fe"];
      clean [label="Clean"];
      model [label="Model", fillcolor="#dcfce7"];
      review [label="Human review", shape=diamond, fillcolor="#fef3c7"];
      publish [label="Publish", fillcolor="#fae8ff"];

      collect -> clean -> model -> review -> publish;
      review -> clean [label="needs fixes", style=dashed, color="#b45309"];
    }
    """
    return (style_dot,)


@app.cell
def _(dot, mo, style_dot):
    mo.vstack(
        [
            mo.md(
                """
                ## 2. Style is part of the language

                DOT has graph, node, and edge attributes. The
                [Graphviz attribute reference](https://graphviz.org/doc/info/attrs.html)
                covers the full vocabulary; here we only need a few basics:
                direction, spacing, shapes, colors, line styles, labels, and
                typography.
                """
            ),
            dot(style_dot),
        ]
    )
    return


@app.cell
def _():
    architecture_dot = """
    digraph {
      graph [
        rankdir=LR,
        bgcolor="transparent",
        pad=0.28,
        nodesep=0.55,
        ranksep=1.00,
        compound=true,
        fontname="Helvetica"
      ];
      node [
        shape=box,
        style="rounded,filled",
        fontname="Helvetica",
        fontsize=11,
        margin="0.15,0.09",
        color="#314158",
        penwidth=1.2,
        fillcolor="#f8fafc"
      ];
      edge [fontname="Helvetica", fontsize=9, color="#64748b", arrowsize=0.7];

      subgraph cluster_sources {
        label="Inputs";
        style="rounded,filled";
        color="#bfdbfe";
        fillcolor="#eff6ff";
        tickets [label="Tickets", fillcolor="#dbeafe"];
        docs [label="Docs", fillcolor="#dbeafe"];
        metrics [label="Metrics", fillcolor="#dbeafe"];
      }

      subgraph cluster_reasoning {
        label="Analysis";
        style="rounded,filled";
        color="#bbf7d0";
        fillcolor="#f0fdf4";
        parse [label="Parse"];
        link [label="Link context"];
        rank [label="Rank signals"];
      }

      subgraph cluster_outputs {
        label="Outputs";
        style="rounded,filled";
        color="#f5d0fe";
        fillcolor="#fdf4ff";
        summary [label="Summary", fillcolor="#fae8ff"];
        chart [label="Chart", fillcolor="#fae8ff"];
        actions [label="Next actions", fillcolor="#fae8ff"];
      }

      tickets -> parse;
      docs -> parse;
      metrics -> rank;
      parse -> link -> rank;
      rank -> summary;
      rank -> chart;
      link -> actions;
      actions -> tickets [label="follow up", style=dashed, color="#9333ea"];
    }
    """
    return (architecture_dot,)


@app.cell
def _(architecture_dot, dot, mo):
    mo.vstack(
        [
            mo.md(
                """
                ## 3. Clusters make architecture diagrams readable

                Graphviz clusters group related nodes without forcing you to
                manually position every box. The layout still follows the
                graph, but the diagram has clear visual sections.
                """
            ),
            dot(architecture_dot),
        ]
    )
    return


@app.cell
def _():
    network_dot = """
    graph {
      graph [
        bgcolor="transparent",
        pad=0.25,
        overlap=false,
        splines=true,
        outputorder=edgesfirst
      ];
      node [
        shape=circle,
        style=filled,
        fixedsize=true,
        width=0.48,
        fontname="Helvetica",
        fontsize=10,
        color="#334155",
        fillcolor="#f8fafc"
      ];
      edge [color="#94a3b8", penwidth=1.2];

      a [label="A", fillcolor="#dbeafe"];
      b [label="B", fillcolor="#dbeafe"];
      c [label="C", fillcolor="#dcfce7"];
      d [label="D", fillcolor="#dcfce7"];
      e [label="E", fillcolor="#fae8ff"];
      f [label="F", fillcolor="#fae8ff"];
      g [label="G", fillcolor="#fef3c7"];
      h [label="H", fillcolor="#fef3c7"];
      i [label="I"];
      j [label="J"];
      k [label="K"];
      l [label="L"];

      a -- b; a -- c; a -- d; b -- c; c -- d;
      e -- f; e -- g; f -- h; g -- h;
      i -- j; j -- k; k -- l; l -- i; i -- k;
      d -- e; c -- i; h -- j; b -- l;
    }
    """
    return (network_dot,)


@app.cell
def _(dot, mo, network_dot):
    mo.vstack(
        [
            mo.md(
                """
                ## 4. The same DOT can use different Graphviz engines

                `dot` is ideal for layered diagrams. Other
                [Graphviz layout engines](https://graphviz.org/docs/layouts/)
                like `neato`, `fdp`, `sfdp`, `circo`, and `twopi` are useful
                for undirected networks where relative proximity matters more
                than strict top-to-bottom flow.
                """
            ),
            mo.hstack(
                [
                    mo.vstack([mo.md("**neato**"), dot(network_dot, engine="neato", fit=True)]),
                    mo.vstack([mo.md("**fdp**"), dot(network_dot, engine="fdp", fit=True)]),
                    mo.vstack([mo.md("**circo**"), dot(network_dot, engine="circo", fit=True)]),
                ],
                wrap=True,
                gap=2,
            ),
        ]
    )
    return


@app.cell
def _():
    state_machine_dot = """
    digraph {
      graph [
        rankdir=LR,
        bgcolor="transparent",
        pad=0.20,
        nodesep=0.50,
        ranksep=0.85
      ];
      node [
        shape=circle,
        style=filled,
        fixedsize=true,
        width=0.75,
        fontname="Helvetica",
        fontsize=10,
        color="#334155",
        fillcolor="#f8fafc"
      ];
      edge [fontname="Helvetica", fontsize=9, color="#64748b", arrowsize=0.7];

      start [label="", shape=point, width=0.12, fillcolor="#334155"];
      idle [label="Idle", fillcolor="#dbeafe"];
      draft [label="Draft", fillcolor="#fef3c7"];
      review [label="Review", fillcolor="#fae8ff"];
      live [label="Live", fillcolor="#dcfce7"];
      archived [label="Archive"];

      start -> idle;
      idle -> draft [label="create"];
      draft -> review [label="submit"];
      review -> draft [label="changes", style=dashed, color="#b45309"];
      review -> live [label="approve"];
      live -> archived [label="retire"];
      archived -> draft [label="restore", style=dashed];
    }
    """
    return (state_machine_dot,)


@app.cell
def _(dot, mo, state_machine_dot):
    mo.vstack(
        [
            mo.md(
                """
                ## 5. DOT works well for generated diagrams

                Because DOT is just text, you can write it by hand, template it,
                or generate it from Python objects. That makes it useful for
                diagrams that need to stay close to real code and data.
                """
            ),
            dot(state_machine_dot),
            mo.md(
                r'''
                ```python
                import easydot

                easydot.render("""
                digraph {
                  draft -> review -> live;
                  review -> draft [label="changes", style=dashed];
                }
                """)
                ```
                '''
            ),
        ]
    )
    return


@app.cell
def _(mo):
    active_step = mo.ui.slider(
        start=1,
        stop=4,
        step=1,
        value=1,
        label="Pipeline step",
        show_value=True,
        full_width=True,
    )
    return (active_step,)


@app.cell
def _(active_step, dot, mo):
    steps = [
        ("ingest", "Ingest"),
        ("validate", "Validate"),
        ("enrich", "Enrich"),
        ("publish", "Publish"),
    ]
    active_index = int(active_step.value) - 1

    def fill(index: int) -> str:
        if index < active_index:
            return "#dcfce7"
        if index == active_index:
            return "#fef3c7"
        return "#f8fafc"

    nodes = "\n".join(
        f'      {node} [label="{label}", fillcolor="{fill(index)}"];'
        for index, (node, label) in enumerate(steps)
    )
    edges = " -> ".join(node for node, _label in steps)
    active_label = steps[active_index][1]
    interactive_dot = f"""
    digraph {{
      graph [
        rankdir=LR,
        bgcolor="transparent",
        pad=0.22,
        nodesep=0.50,
        ranksep=0.90
      ];
      node [
        shape=box,
        style="rounded,filled",
        fontname="Helvetica",
        fontsize=12,
        margin="0.16,0.10",
        color="#334155",
        penwidth=1.4
      ];
      edge [fontname="Helvetica", color="#64748b", arrowsize=0.75];

    {nodes}
      {edges};
    }}
    """

    mo.vstack(
        [
            mo.md(
                f"""
                ## 6. Marimo makes DOT reactive

                Marimo UI elements expose a `.value`. When that value changes,
                cells that reference it rerun, so the DOT source can be
                regenerated and `easydot` can render the new graph. Current
                step: **{active_label}**.
                """
            ),
            active_step,
            dot(interactive_dot),
        ]
    )
    return


@app.cell
def _():
    animated_dot = """
    digraph {
      graph [
        rankdir=LR,
        bgcolor="transparent",
        pad=0.25,
        nodesep=0.58,
        ranksep=0.90
      ];
      node [
        shape=box,
        style="rounded,filled",
        fontname="Helvetica",
        fontsize=12,
        margin="0.16,0.10",
        color="#334155",
        penwidth=1.4,
        fillcolor="#f8fafc"
      ];
      edge [
        fontname="Helvetica",
        fontsize=10,
        color="#64748b",
        penwidth=1.8,
        arrowsize=0.75
      ];

      source [id="pulse_source", label="DOT", fillcolor="#dbeafe"];
      render [id="pulse_render", label="Graphviz", fillcolor="#dcfce7"];
      svg [id="pulse_svg", label="SVG", fillcolor="#fef3c7"];
      notebook [id="pulse_notebook", label="marimo", fillcolor="#fae8ff"];

      source -> render [id="flow_1", label="layout"];
      render -> svg [id="flow_2", label="draw"];
      svg -> notebook [id="flow_3", label="display"];
    }
    """
    return (animated_dot,)


@app.cell
def _(animated_dot, dot, easydot, mo):
    def animate_svg(svg: str) -> str:
        svg = svg[svg.find("<svg") :]
        styles = """
        <style>
          .edge path {
            stroke-dasharray: 9 7;
            animation: easydot-flow 900ms linear infinite;
          }
          #pulse_source polygon,
          #pulse_render polygon,
          #pulse_svg polygon,
          #pulse_notebook polygon {
            transform-box: fill-box;
            transform-origin: center;
            animation: easydot-pulse 1800ms ease-in-out infinite;
          }
          #pulse_render polygon { animation-delay: 200ms; }
          #pulse_svg polygon { animation-delay: 400ms; }
          #pulse_notebook polygon { animation-delay: 600ms; }
          @keyframes easydot-flow {
            to { stroke-dashoffset: -32; }
          }
          @keyframes easydot-pulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.06); }
          }
        </style>
        """
        return svg.replace(">", f">{styles}", 1)

    try:
        animated_svg = animate_svg(easydot.svg(animated_dot, backend="wasm"))
        output = mo.Html(animated_svg)
    except RuntimeError:
        output = mo.vstack(
            [
                dot(animated_dot),
                mo.md(
                    """
                    This environment is using browser rendering only, so the
                    notebook shows the regular easydot diagram here. The CSS
                    animation version needs a synchronous SVG backend:

                    ```bash
                    uv run --with wasi-graphviz --with wasmtime marimo edit examples/intro.py
                    ```
                    """
                ),
            ]
        )

    mo.vstack(
        [
            mo.md(
                """
                ## 7. SVG output can be styled and animated

                Browser rendering is great for notebooks, but when a
                synchronous backend is available, `easydot.svg()` returns the
                raw SVG string. Because Graphviz preserves SVG ids, we can add
                CSS animations around the generated diagram.
                """
            ),
            output,
        ]
    )
    return


@app.cell(hide_code=True)
def _(easydot, mo):
    from textwrap import dedent

    caps = easydot.capabilities(check_cdn=False)
    rows = "\n".join(
        f"- `{name}`: {'available' if capability.available else 'not available'}"
        for name, capability in caps.items()
    )
    mo.md(dedent(f"""
    ## 8. Notebook first, with other backends when available

    This notebook uses the browser backend so it can run in hosted marimo
    environments without installing Graphviz system binaries. The same API
    can also use a Python-side WASM backend through
    [`wasi-graphviz`](https://github.com/pablormier/wasi-graphviz) or a native
    Graphviz installation when those are present.

    Current runtime:

    {rows}

    The main call is intentionally small:

    ```python
    easydot.render(dot_source, fit="horizontal")
    ```
    """))
    return


@app.cell
def _(mo):
    mo.md("""
    ## 9. Try it

    Change any DOT string above and rerun the cell. Good experiments:

    - switch `rankdir=LR` to `rankdir=TB`
    - add a new edge and let Graphviz rearrange the diagram
    - change a node shape to `ellipse`, `diamond`, `cylinder`, or `note`
    - try a different engine for the network graph

    The important idea is that diagram layout becomes code: portable,
    reviewable, and easy to regenerate.

    ## Project note

    [`easydot`](https://github.com/pablormier/easydot) is an independent
    Python package. It is not an official Graphviz project. The value of
    `easydot` is packaging and display:
    it gives notebooks a small Python API, convenient rich outputs, and
    browser-friendly rendering through the Graphviz engine compiled to
    WebAssembly. For Python-side WASM rendering, `easydot` uses the separate
    [`wasi-graphviz`](https://github.com/pablormier/wasi-graphviz) project.

    For the original project, documentation, and license details, visit
    [graphviz.org](https://graphviz.org/).
    """)
    return


if __name__ == "__main__":
    app.run()
