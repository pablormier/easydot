import marimo

__generated_with = "0.23.1"
app = marimo.App(width="full")


@app.cell
def _():
    import marimo as mo

    import easydot

    return easydot, mo


@app.cell
def _(mo):
    mo.md(r"""
    # easydot showcase

    Browser-side Graphviz rendering with fit modes, engines, toolbar controls,
    and marimo iframe integration.

    ```bash
    uv run marimo edit examples/demo.py
    ```
    """)
    return


@app.cell
def _():
    architecture_dot = """
    digraph G {
      graph [
        rankdir=LR,
        bgcolor="transparent",
        pad=0.25,
        nodesep=0.55,
        ranksep=0.95,
        fontname="Helvetica"
      ];
      node [
        shape=box,
        style="rounded,filled",
        fontname="Helvetica",
        fontsize=12,
        margin="0.16,0.10",
        color="#2f4050",
        penwidth=1.2,
        fillcolor="#f7f9fb"
      ];
      edge [fontname="Helvetica", fontsize=10, color="#667085", arrowsize=0.75];

      subgraph cluster_sources {
        label="Signals";
        color="#d7e4f2";
        style="rounded,filled";
        fillcolor="#f8fbff";
        pos [label="Point of sale", fillcolor="#e5f0ff"];
        stock [label="Inventory", fillcolor="#e5f0ff"];
        crm [label="Customers", fillcolor="#e5f0ff"];
      }

      subgraph cluster_stream {
        label="Stream";
        color="#d9ead7";
        style="rounded,filled";
        fillcolor="#fbfffa";
        ingest [label="Ingest"];
        normalize [label="Normalize"];
        score [label="Score"];
      }

      subgraph cluster_store {
        label="State";
        color="#f1dfb6";
        style="rounded,filled";
        fillcolor="#fffaf0";
        warehouse [shape=cylinder, label="Warehouse", fillcolor="#fff0c2"];
        cache [shape=cylinder, label="Cache", fillcolor="#fff0c2"];
      }

      subgraph cluster_delivery {
        label="Delivery";
        color="#ead7dc";
        style="rounded,filled";
        fillcolor="#fff8fa";
        dashboard [label="Operator view", fillcolor="#ffe6ec"];
        api [label="API", fillcolor="#ffe6ec"];
        alerts [label="Alerts", fillcolor="#ffe6ec"];
      }

      pos -> ingest;
      stock -> ingest;
      crm -> ingest;
      ingest -> normalize -> score;
      normalize -> warehouse;
      score -> cache;
      warehouse -> dashboard;
      cache -> api;
      score -> alerts [label="threshold"];
      api -> dashboard [style=dashed, label="drilldown"];
    }
    """
    return (architecture_dot,)


@app.cell
def _(architecture_dot, easydot, mo):
    mo.vstack(
        [
            mo.md("## 1. A richer default render"),
            easydot.display(architecture_dot, fit=True),
        ]
    )
    return


@app.cell
def _():
    tree_dot = """
    digraph G {
      graph [
        rankdir=TB,
        bgcolor="transparent",
        pad=0.25,
        nodesep=0.42,
        ranksep=0.60,
        ordering=out
      ];
      node [
        shape=box,
        style="rounded,filled",
        fontname="Helvetica",
        fontsize=11,
        color="#394b59",
        fillcolor="#f7f9fb",
        margin="0.14,0.08"
      ];
      edge [color="#7a8699", arrowsize=0.65];

      root [label="Release", fillcolor="#e3efff", penwidth=1.5];
      plan [label="Plan"];
      build [label="Build"];
      verify [label="Verify"];
      ship [label="Ship"];
      root -> {plan build verify ship};

      scope [label="Scope"];
      design [label="Design"];
      risks [label="Risks"];
      plan -> {scope design risks};

      package [label="Package"];
      docs [label="Docs"];
      assets [label="Assets"];
      build -> {package docs assets};

      tests [label="Tests"];
      qa [label="QA"];
      review [label="Review"];
      verify -> {tests qa review};

      tag [label="Tag"];
      publish [label="Publish"];
      announce [label="Announce"];
      ship -> {tag publish announce};
    }
    """
    return (tree_dot,)


@app.cell
def _(easydot, mo, tree_dot):
    mo.vstack(
        [
            mo.md("## 2. Tree layout"),
            easydot.display(tree_dot, fit=True),
        ]
    )
    return


@app.cell
def _():
    wide_dot = """
    digraph G {
      graph [
        rankdir=LR,
        bgcolor="transparent",
        pad=0.25,
        nodesep=0.38,
        ranksep=0.90,
        splines=ortho
      ];
      node [
        shape=box,
        style="rounded,filled",
        fontname="Helvetica",
        fontsize=11,
        margin="0.13,0.08",
        color="#2f4050",
        fillcolor="#f8fafc"
      ];
      edge [color="#667085", arrowsize=0.65];

      receive [label="Receive"];
      classify [label="Classify"];
      parse [label="Parse"];
      validate [label="Validate"];
      enrich [label="Enrich"];
      match [label="Match"];
      price [label="Price"];
      allocate [label="Allocate"];
      forecast [label="Forecast"];
      publish [label="Publish"];
      observe [label="Observe"];
      archive [label="Archive"];

      receive -> classify -> parse -> validate -> enrich -> match -> price -> allocate -> forecast -> publish -> observe -> archive;
      validate -> reject [label="invalid", style=dashed, color="#b42318"];
      enrich -> profile [label="lookup", style=dashed];
      match -> review [label="low confidence", style=dashed];
      observe -> alert [label="anomaly", style=dashed, color="#b42318"];
    }
    """
    return (wide_dot,)


@app.cell
def _(easydot, mo, wide_dot):
    mo.vstack(
        [
            mo.md("## 3. Horizontal fit"),
            mo.hstack(
                [
                    mo.vstack(
                        [
                            mo.md("**Natural size**"),
                            easydot.display(wide_dot, fit=False),
                        ]
                    ),
                    mo.vstack(
                        [
                            mo.md("**`fit='horizontal'`**"),
                            easydot.display(wide_dot, fit="horizontal"),
                        ]
                    ),
                    mo.vstack(
                        [
                            mo.md("**`fit=True`**"),
                            easydot.display(wide_dot, fit=True),
                        ]
                    ),
                ],
                wrap=True,
            ),
        ]
    )
    return


@app.cell
def _():
    chain = " -> ".join(f"stage_{i:02d}" for i in range(28))
    tall_dot = f"""
    digraph G {{
      graph [
        rankdir=TB,
        bgcolor="transparent",
        pad=0.20,
        nodesep=0.22,
        ranksep=0.32
      ];
      node [
        shape=box,
        style="rounded,filled",
        fontname="Helvetica",
        fontsize=10,
        margin="0.10,0.05",
        color="#3d4a5c",
        fillcolor="#eef5ff"
      ];
      edge [color="#8a98aa", arrowsize=0.55];
      {chain};
    }}
    """
    return (tall_dot,)


@app.cell
def _(easydot, mo, tall_dot):
    mo.vstack(
        [
            mo.md("## 4. Vertical fit with an explicit viewport"),
            mo.hstack(
                [
                    mo.vstack(
                        [
                            mo.md("**Natural size**"),
                            easydot.display(tall_dot, fit=False, iframe_height="360px"),
                        ]
                    ),
                    mo.vstack(
                        [
                            mo.md("**`fit='vertical'`**"),
                            easydot.display(tall_dot, fit="vertical", iframe_height="360px"),
                        ]
                    ),
                    mo.vstack(
                        [
                            mo.md("**`fit=True`**"),
                            easydot.display(tall_dot, fit=True, iframe_height="360px"),
                        ]
                    ),
                ],
                wrap=True,
            ),
        ]
    )
    return


@app.cell
def _(easydot, mo, tree_dot):
    mo.vstack(
        [
            mo.md("## 5. Scale"),
            mo.hstack(
                [
                    mo.vstack(
                        [
                            mo.md(f"**`scale={scale}`**"),
                            easydot.display(tree_dot, scale=scale),
                        ]
                    )
                    for scale in (0.25, 0.5, 1.0, 1.5)
                ],
                wrap=True,
            ),
        ]
    )
    return


@app.cell
def _(architecture_dot, easydot, mo):
    mo.vstack(
        [
            mo.md("## 6. Toolbar"),
            mo.hstack(
                [
                    mo.vstack(
                        [
                            mo.md("**Toolbar on**"),
                            easydot.display(architecture_dot, fit=True, toolbar=True),
                        ]
                    ),
                    mo.vstack(
                        [
                            mo.md("**Toolbar off**"),
                            easydot.display(architecture_dot, fit=True, toolbar=False),
                        ]
                    ),
                ],
                wrap=True,
            ),
        ]
    )
    return


@app.cell
def _(easydot, mo):
    engine_dot = """
    graph G {
      graph [bgcolor="transparent", pad=0.18, nodesep=0.35, ranksep=0.55];
      node [
        shape=circle,
        style=filled,
        fontname="Helvetica",
        fontsize=10,
        width=0.44,
        fixedsize=true,
        color="#405063",
        fillcolor="#edf4ff"
      ];
      edge [color="#69778a"];
      A -- B; A -- C; A -- D; A -- E;
      B -- C; C -- D; D -- E; E -- B;
      B -- F; C -- G; D -- H; E -- I;
      F -- G; G -- H; H -- I; I -- F;
    }
    """
    mo.vstack(
        [
            mo.md("## 7. Engines"),
            mo.hstack(
                [
                    mo.vstack(
                        [
                            mo.md(f"**{engine}**"),
                            easydot.display(engine_dot, engine=engine, fit=True),
                        ]
                    )
                    for engine in ("dot", "neato", "fdp", "sfdp", "circo", "twopi")
                ],
                wrap=True,
            ),
        ]
    )
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## 8. Non-iframe mode

    Passing `iframe=False` skips the iframe wrapper. That is useful when
    embedding into a page that already provides layout and executes script
    tags.

    Marimo does not execute scripts from plain HTML outputs, so this mode is
    not rendered in this demo:

    ```python
    easydot.display(tree_dot, iframe=False)
    ```
    """)
    return


if __name__ == "__main__":
    app.run()
