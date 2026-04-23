<div align="center">

<img src="assets/easydot-logo.png" alt="easydot" width="300">

**Graphviz rendered in the browser, from one line of Python. 100% client-side.**

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-3776ab?logo=python&logoColor=white)](https://www.python.org)
[![pip install easydot](https://img.shields.io/badge/pip%20install-easydot-blue?logo=pypi&logoColor=white)](https://pypi.org/project/easydot/)
[![License: BSD-3-Clause](https://img.shields.io/badge/license-BSD--3--Clause-green)](LICENSE)
[![No Dependencies](https://img.shields.io/badge/dependencies-0-brightgreen)]()
[![marimo](https://marimo.io/shield.svg)](https://marimo.app/l/939bsu)

</div>

```bash
pip install easydot
```

```python
import easydot

easydot.display("digraph { A -> B -> C }")
```

## Example

<img src="assets/example.png" alt="easydot example" width="800px">

---

## 💡 Why easydot

Graphviz usually requires a native `dot` binary. That's fine on a laptop, but painful in CI images, slim containers, shared clusters, and browser runtimes like JupyterLite, Pyodide, or marimo. `easydot` packages browser rendering so `pip install easydot` is enough for notebooks.

- **Pip-installable.** No `brew`, no `conda`, no `apt-get`, no Dockerfile changes.
- **Browser rendering.** Layout runs client-side via [Graphviz WASM](https://github.com/hpcc-systems/hpcc-js-wasm), so it works inside sandboxed kernels and restricted hosts.
- **Tiny notebook outputs.** The WASM bundle is vendored and served once over loopback instead of inlined into every cell.
- **Works offline.** Assets ship in the package, with a local fallback when the CDN isn't reachable.
- **Small API.** `easydot.display(...)` renders via `_repr_html_` in notebooks.

## 🔤 Why DOT

DOT is a small text format for graph diagrams. Many Python libraries and build tools can generate it.

- **Common output format.** [NetworkX](https://networkx.org/), [pydot](https://pypi.org/project/pydot/), [pygraphviz](https://pygraphviz.github.io/), [scikit-learn](https://scikit-learn.org) decision trees, [PyTorch](https://pytorch.org) and [TensorFlow](https://www.tensorflow.org) model viz, [Dask](https://www.dask.org/) task graphs, [Airflow](https://airflow.apache.org/) DAGs, Terraform, Bazel, Ninja, `gprof2dot`, and other tools can emit DOT.
- **LLM-friendly.** Models can usually generate DOT for architecture diagrams, state machines, and dependency graphs.
- **Plain text.** Diffs cleanly, templates easily, pipes nicely.
- **Graphviz features.** Five layout engines (`dot`, `neato`, `fdp`, `circo`, `twopi`), clusters, HTML-like labels, and styling.

## 🚀 Usage

### pydot

```bash
pip install easydot[pydot]
```

```python
import easydot, pydot

graph = pydot.Dot("example", graph_type="digraph")
graph.add_edge(pydot.Edge("A", "B"))

easydot.display(graph)
```

### NetworkX

```python
import easydot, networkx as nx
from networkx.drawing.nx_pydot import to_pydot

G = nx.DiGraph([("A", "B"), ("B", "C"), ("A", "C")])
easydot.display(to_pydot(G))
```

### CLI

```bash
echo 'digraph { A -> B }' | easydot     # render DOT to HTML on stdout
easydot --urls                          # print local asset server URLs
```

## 🔀 Source Modes

By default, `easydot` tries a pinned CDN URL first and falls back to the local server.

| Mode    | Local | CDN | Best for                                               |
| ------- | :---: | :-: | ------------------------------------------------------ |
| `auto`  |  yes  | yes | Most setups (default; CDN first, then local fallback)  |
| `local` |  yes  | no  | Offline environments with no internet access           |
| `cdn`   |  no   | yes | Remote hosts where `127.0.0.1` isn't browser-reachable |

```python
easydot.display("digraph { A -> B }", source="cdn")
```

<details>
<summary><b>Environment variables</b></summary>

Set a notebook-wide default without editing every call:

```python
import os
os.environ["EASYDOT_SOURCE"] = "cdn"   # auto | local | cdn
```

Only applies when `source="auto"`. Explicit `source=` arguments still win.

For hosted marimo environments that protect generated iframe file URLs, force a self-contained iframe:

```python
os.environ["EASYDOT_IFRAME_MODE"] = "srcdoc"   # auto | marimo | srcdoc | data
```

PyCharm notebooks are detected automatically and use a `data:` iframe because
their output recycling can detach and reattach `srcdoc` iframes while scrolling.
You can force that wrapper explicitly with `EASYDOT_IFRAME_MODE="data"`.

The same modes are available per display call:

```python
easydot.display("digraph { A -> B }", iframe_mode="data")
```

</details>

## 📓 marimo

Works out of the box. `easydot` detects marimo and uses its iframe display helper automatically, since marimo doesn't execute inline scripts from plain `text/html` outputs. All source modes work.

```bash
uv run marimo edit examples/demo.py                                   # edit the demo
uv run marimo run examples/demo.py --headless --port 2718 --no-token  # read-only preview
```

## ⏳ Large Graphs

Browser rendering is asynchronous relative to notebook cell execution: a cell
can finish before the browser has loaded Graphviz WASM and produced the SVG.
By default, `easydot` renders on the output iframe's main thread and shows an
in-progress indicator while the graph is rendering. You can opt into Web Worker
rendering for large graphs.

```python
easydot.display(dot, worker=False)   # default: render on the output iframe's main thread
easydot.display(dot, worker="auto")  # try a worker, visibly fall back if unavailable
easydot.display(dot, worker=True)    # require a worker; no main-thread fallback
```

If worker rendering is unavailable and `worker="auto"` is used, `easydot` shows
a warning before falling back to main-thread rendering. Large graphs may freeze
that output iframe until Graphviz finishes in fallback mode.

## 🔌 Library Integration

For libraries that generate their own HTML, use the lower-level asset API:

```python
from easydot import asset_urls

js_url = asset_urls()["js"]
```

```js
const mod = await import(jsUrl);
const graphviz = await mod.Graphviz.load();
const svg = graphviz.layout("digraph { A -> B }", "svg", "dot");
```

> Need server-side rendering to files? Use native Graphviz or the [`graphviz`](https://pypi.org/project/graphviz/) Python package. `easydot` is browser-only by design.

<details>
<summary><b>Runtime model</b></summary>

The asset server is intentionally narrow:

- Binds only to `127.0.0.1`
- OS-assigned ephemeral port
- Serves only known packaged files (no directory browsing)
- Long-lived cache headers
- Shuts down automatically when the Python process exits

</details>

## 📜 License

| Component              | License                                                                                                                                      |
| ---------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| `easydot` Python code  | [BSD-3-Clause](LICENSE)                                                                                                                      |
| Vendored Graphviz WASM | Apache-2.0, from [`@hpcc-js/wasm-graphviz`](https://www.npmjs.com/package/@hpcc-js/wasm-graphviz). Pinned version in `src/easydot/_version.py` |
