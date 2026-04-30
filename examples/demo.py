import marimo

__generated_with = "0.23.4"
app = marimo.App(width="full")


@app.cell
def _():
    import marimo as mo
    import easydot

    return easydot, mo


@app.cell
def _(mo):
    mo.md(r"""
    Render Graphviz DOT inside browser notebooks without installing Graphviz
    binaries. `easydot` ships the WebAssembly renderer, handles notebook
    display integration, and keeps the output small by loading the renderer
    from a local asset server or CDN.

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
            mo.md("## 1. Notebook-native DOT rendering"),
            easydot.render(architecture_dot, fit=True),
        ]
    )
    return


@app.cell
def _():
    biology_dot = """
    digraph G {
      graph [
        rankdir=LR,
        bgcolor="transparent",
        pad=0.30,
        nodesep=0.42,
        ranksep=0.90,
        splines=true,
        compound=true,
        fontname="Helvetica"
      ];
      node [
        shape=box,
        style="rounded,filled",
        fontname="Helvetica",
        fontsize=11,
        margin="0.14,0.08",
        color="#36515f",
        fillcolor="#f8fbfc"
      ];
      edge [fontname="Helvetica", fontsize=9, color="#637381", arrowsize=0.65];

      subgraph cluster_membrane {
        label="Membrane";
        color="#d5e7f2";
        style="rounded,filled";
        fillcolor="#f6fbff";
        egf [label="EGF", shape=oval, fillcolor="#dff1ff"];
        tgfb [label="TGF-beta", shape=oval, fillcolor="#dff1ff"];
        egfr [label="EGFR"];
        tgfbr [label="TGFBR"];
        integrin [label="Integrin"];
      }

      subgraph cluster_signaling {
        label="Signaling";
        color="#d8ead5";
        style="rounded,filled";
        fillcolor="#fbfffa";
        ras [label="RAS"];
        raf [label="RAF"];
        mek [label="MEK"];
        erk [label="ERK"];
        pi3k [label="PI3K"];
        akt [label="AKT"];
        mtor [label="mTOR"];
        smad [label="SMAD2/3"];
        fak [label="FAK"];
        nfkb [label="NF-kB"];
      }

      subgraph cluster_nucleus {
        label="Nucleus";
        color="#eadfc4";
        style="rounded,filled";
        fillcolor="#fffaf0";
        myc [label="MYC"];
        hif [label="HIF1A"];
        stat3 [label="STAT3"];
        twist [label="TWIST"];
      }

      subgraph cluster_response {
        label="Phenotype";
        color="#efd5dd";
        style="rounded,filled";
        fillcolor="#fff8fa";
        proliferation [label="Proliferation", fillcolor="#ffe8ef"];
        survival [label="Survival", fillcolor="#ffe8ef"];
        invasion [label="Invasion", fillcolor="#ffe8ef"];
        angiogenesis [label="Angiogenesis", fillcolor="#ffe8ef"];
      }

      egf -> egfr;
      tgfb -> tgfbr;
      egfr -> ras -> raf -> mek -> erk -> myc;
      egfr -> pi3k -> akt -> mtor -> hif;
      tgfbr -> smad -> twist;
      integrin -> fak -> nfkb -> stat3;
      akt -> survival;
      myc -> proliferation;
      hif -> angiogenesis;
      twist -> invasion;
      stat3 -> survival;
      nfkb -> proliferation [style=dashed, label="inflammation"];
      mtor -> proliferation [style=dashed];
      smad -> proliferation [color="#b42318", style=dashed, label="context"];
    }
    """
    return (biology_dot,)


@app.cell
def _(biology_dot, easydot, mo):
    mo.vstack(
        [
            mo.md("## 2. Complex DOT without local Graphviz"),
            easydot.render(biology_dot, fit=True),
        ]
    )
    return


@app.cell
def _():
    source_dot = """
    digraph G {
      graph [rankdir=LR, bgcolor="transparent", pad=0.20];
      node [shape=box, style="rounded,filled", fontname="Helvetica", fillcolor="#f7f9fb"];
      dot [label="DOT"];
      wasm [label="Graphviz WASM"];
      svg [label="SVG output"];
      dot -> wasm -> svg;
    }
    """
    return (source_dot,)


@app.cell
def _(easydot, mo, source_dot):
    mo.vstack(
        [
            mo.md("## 3. Source loading"),
            mo.hstack(
                [
                    mo.vstack([mo.md("**`source='auto'`**"), easydot.render(source_dot, backend="browser", source="auto", fit=True)]),
                    mo.vstack([mo.md("**`source='local'`**"), easydot.render(source_dot, backend="browser", source="local", fit=True)]),
                    mo.vstack([mo.md("**`source='cdn'`**"), easydot.render(source_dot, backend="browser", source="cdn", fit=True)]),
                ],
                wrap=True,
            ),
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
            mo.md("## 4. Fit modes for notebook cells"),
            mo.hstack(
                [
                    mo.vstack([mo.md("**Natural size**"), easydot.render(wide_dot, fit=False)]),
                    mo.vstack([mo.md("**`fit='horizontal'`**"), easydot.render(wide_dot, fit="horizontal")]),
                    mo.vstack([mo.md("**`fit=True`**"), easydot.render(wide_dot, fit=True)]),
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
            mo.md("## 5. Vertical fit with an explicit viewport"),
            mo.hstack(
                [
                    mo.vstack(
                        [
                            mo.md("**Natural size**"),
                            easydot.render(tall_dot, fit=False, iframe_height="360px"),
                        ]
                    ),
                    mo.vstack(
                        [
                            mo.md("**`fit='vertical'`**"),
                            easydot.render(tall_dot, fit="vertical", iframe_height="360px"),
                        ]
                    ),
                    mo.vstack(
                        [
                            mo.md("**`fit=True`**"),
                            easydot.render(tall_dot, fit=True, iframe_height="360px"),
                        ]
                    ),
                ],
                wrap=True,
            ),
        ]
    )
    return


@app.cell
def _(biology_dot, easydot, mo):
    mo.vstack(
        [
            mo.md("## 6. Scale and toolbar"),
            mo.hstack(
                [
                    mo.vstack([mo.md("**`scale=0.7`**"), easydot.render(biology_dot, scale=0.7)]),
                    mo.vstack([mo.md("**`scale=1.15`**"), easydot.render(biology_dot, scale=1.15)]),
                    mo.vstack([mo.md("**Toolbar off**"), easydot.render(biology_dot, fit=True, toolbar=False)]),
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
            mo.md("## 7. Engine selection"),
            mo.hstack(
                [
                    mo.vstack([mo.md(f"**{engine}**"), easydot.render(engine_dot, engine=engine, fit=True)])
                    for engine in ("dot", "neato", "fdp", "sfdp", "circo", "twopi")
                ],
                wrap=True,
            ),
        ]
    )
    return


@app.cell
def _(easydot, mo, source_dot):
    mo.vstack(
        [
            mo.md("## 8. Worker rendering"),
            mo.hstack(
                [
                    mo.vstack([mo.md("**default (`worker=False`)**"), easydot.render(source_dot, backend="browser", fit=True)]),
                    mo.vstack([mo.md("**`worker='auto'`**"), easydot.render(source_dot, backend="browser", worker="auto", fit=True)]),
                    mo.vstack([mo.md("**`worker=True`**"), easydot.render(source_dot, backend="browser", worker=True, fit=True)]),
                ],
                wrap=True,
            ),
        ]
    )
    return


@app.cell
def _():
    import random

    rng = random.Random(7)
    node_count = 800
    random_edges = {
        (rng.randrange(node_count), rng.randrange(node_count))
        for _ in range(2500)
    }
    large_edges = "\n".join(
        f"n{source:04d} -> n{target:04d};"
        for source, target in sorted(random_edges)
        if source != target
    )
    large_dot = f"""
    digraph G {{
      graph [layout=sfdp, bgcolor="transparent", pad=0.20, overlap=false];
      node [
        shape=point,
        fontname="Helvetica",
        width=0.035,
        color="#405063"
      ];
      edge [color="#8a98aa", arrowsize=0.30];
      {large_edges}
    }}
    """
    return (large_dot,)


@app.cell
def _(easydot, large_dot, mo):
    mo.vstack(
        [
            mo.md("## 9. Large graph rendering"),
            mo.md("Random 1000-node graph rendered with `engine='sfdp'` and `worker=True`."),
            easydot.render(large_dot, engine="sfdp", worker=True, fit="horizontal", backend="browser"),
        ]
    )
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## 10. Non-iframe mode

    Passing `iframe=False` skips the iframe wrapper. That is useful when
    embedding into a page that already provides layout and executes script
    tags.

    Marimo does not execute scripts from plain HTML outputs, so this mode is
    not rendered in this demo:

    ```python
    easydot.render(biology_dot, iframe=False)
    ```
    """)
    return


@app.cell
def _(easydot, mo, source_dot):
    caps = easydot.capabilities()
    cells = []
    for _backend in ("browser", "wasm", "native"):
        if caps[_backend].available:
            cells.append(
                mo.vstack([
                    mo.md(f"**`backend='{_backend}'`**"),
                    easydot.render(source_dot, backend=_backend, fit="horizontal"),
                ])
            )
    return mo.vstack([
        mo.md("## 11. Fit works on all backends"),
        mo.md("`fit='horizontal'` applied to each available backend — same CSS classes, same layout."),
        mo.hstack(cells, wrap=True),
    ])


@app.cell
def _(easydot, mo, source_dot):
    return mo.vstack([
        mo.md("## 12. Raw SVG from wasm/native"),
        mo.md("`easydot.svg()` returns a plain SVG string synchronously. "
              "Only wasm and native backends are supported."),
        mo.code(easydot.svg(source_dot, backend="auto")[:500] + "..."),
    ])


if __name__ == "__main__":
    app.run()
