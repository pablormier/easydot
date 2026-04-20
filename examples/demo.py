import marimo

__generated_with = "0.23.1"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo

    import easydot

    return easydot, mo


@app.cell
def _(mo):
    mo.md(r"""
    # easydot showcase

    This notebook exercises every rendering option in `easydot` against a
    variety of DOT graphs. It doubles as a manual test harness — launch it
    with:

    ```bash
    uv run marimo edit examples/demo.py
    ```
    """)
    return


@app.cell
def _(mo):
    mo.md("""
    ## 1. Basic rendering
    """)
    return


@app.cell
def _(easydot):
    simple_dot = """
    digraph G {
      rankdir=LR;
      A -> B -> C;
      A -> C;
    }
    """
    easydot.display(simple_dot)
    return (simple_dot,)


@app.cell
def _(mo):
    mo.md(r"""
    ## 2. Engines

    The same undirected graph laid out by every Graphviz engine. `neato`,
    `fdp`, `sfdp` use force-directed layouts; `circo` uses circular;
    `twopi` places nodes radially.
    """)
    return


@app.cell
def _(easydot, mo):
    engine_dot = """
    graph G {
      A -- B; A -- C; A -- D; A -- E;
      B -- C; C -- D; D -- E; E -- B;
      B -- F; C -- G; D -- H; E -- I;
    }
    """
    mo.hstack(
        [
            mo.vstack([mo.md(f"**{engine}**"), easydot.display(engine_dot, engine=engine, fit=True)])
            for engine in ("dot", "neato", "fdp", "sfdp", "circo", "twopi")
        ],
        wrap=True,)
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## 3. Fit modes on a wide graph

    A graph that naturally spans horizontally. Resize the browser to see how
    each fit mode reacts.
    """)
    return


@app.cell
def _():
    wide_dot = """
    digraph G {
      rankdir=LR;
      node [shape=box, style=rounded];
      ingest -> parse -> validate -> normalize -> enrich -> dedupe -> index -> serve -> compile -> analyze -> prune -> destroy;
      ingest -> audit;
      validate -> reject;
      enrich -> cache;
    }
    """
    return (wide_dot,)


@app.cell
def _(easydot, wide_dot):
    easydot.display(wide_dot, fit=False)
    return


@app.cell
def _(easydot, wide_dot):
    easydot.display(wide_dot, fit=True)
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## 4. Fit modes on a tall graph

    A deep vertical chain. Before the new fit modes, `fit=True` would still
    leave a vertical scrollbar — now `fit=True` (both) and `fit='vertical'`
    clamp the height to the iframe.
    """)
    return


@app.cell
def _():
    chain = " -> ".join(f"step_{i:02d}" for i in range(25))
    tall_dot = f"""
    digraph G {{
      rankdir=TB;
      node [shape=box, style=filled, fillcolor="#eef3ff"];
      {chain};
    }}
    """
    return (tall_dot,)


@app.cell
def _(easydot, tall_dot):
    easydot.display(tall_dot, fit=False)
    return


@app.cell
def _(easydot, tall_dot):
    easydot.display(tall_dot, fit="vertical")
    return


@app.cell
def _(easydot, mo, tall_dot):
    mo.hstack(
        [
            mo.md("**`fit=False`** — natural size, vertical scrollbar"),
            easydot.display(tall_dot, fit=False),
            mo.md("**`fit='horizontal'`** — only constrains width, still scrolls vertically"),
            easydot.display(tall_dot, fit="horizontal"),
            mo.md("**`fit='vertical'`** — constrains height to iframe"),
            easydot.display(tall_dot, fit="vertical"),
            mo.md("**`fit=True`** (both) — fills iframe, preserves aspect ratio"),
            easydot.display(tall_dot, fit=True),
        ]
    )
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## 5. Scale

    `scale` multiplies the natural size. With `fit=False` it's the final
    display size; with the fit modes it acts as an upper-bound multiplier.
    """)
    return


@app.cell
def _(easydot, mo, simple_dot):
    mo.hstack(
        [
            mo.vstack([mo.md(f"**`scale={s}`**"), easydot.display(simple_dot, scale=s, iframe_height="200px")])
            for s in (0.75, 1.0, 1.5, 2.0)
        ],
        wrap=True,
    )
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## 6. Toolbar

    The toolbar adds copy/download buttons in the top-right. It appears
    faintly until hovered.
    """)
    return


@app.cell
def _(easydot, mo, simple_dot):
    mo.hstack(
        [
            mo.vstack([mo.md("**`toolbar=True`** (default)"), easydot.display(simple_dot, toolbar=True, iframe_height="200px")]),
            mo.vstack([mo.md("**`toolbar=False`**"), easydot.display(simple_dot, toolbar=False, iframe_height="200px")]),
        ]
    )
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## 7. Clusters, colors, shapes

    A richer example to show off styling.
    """)
    return


@app.cell
def _(easydot):
    styled_dot = """
    digraph G {
      rankdir=LR;
      compound=true;
      node [fontname="Helvetica", fontsize=11];

      subgraph cluster_ingest {
        label="Ingest";
        style=filled; color="#eef3ff";
        kafka [shape=cylinder, fillcolor="#cfe0ff", style=filled];
        webhook [shape=box, fillcolor="#cfe0ff", style=filled];
      }

      subgraph cluster_process {
        label="Process";
        style=filled; color="#f0fff0";
        validate [shape=diamond, fillcolor="#cce8cc", style=filled];
        enrich [shape=box, style="rounded,filled", fillcolor="#cce8cc"];
      }

      subgraph cluster_store {
        label="Store";
        style=filled; color="#fff5e6";
        postgres [shape=cylinder, fillcolor="#ffe0b3", style=filled];
        s3 [shape=cylinder, fillcolor="#ffe0b3", style=filled];
      }

      kafka -> validate;
      webhook -> validate;
      validate -> enrich [label="ok", color="#1a7f37"];
      validate -> s3 [label="reject", color="#b00020", style=dashed];
      enrich -> postgres;
      enrich -> s3;
    }
    """
    easydot.display(styled_dot, fit=True, iframe_height="380px")
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## 8. Non-iframe mode

    Passing `iframe=False` skips the iframe wrapper — useful when embedding
    into a page that already provides layout.
    """)
    return


@app.cell
def _(easydot, simple_dot):
    easydot.display(simple_dot, iframe=False)
    return


if __name__ == "__main__":
    app.run()
