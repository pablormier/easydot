<div align="center">

# easydot

**Graphviz in the browser. Zero installs. One line of Python.**

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-3776ab?logo=python&logoColor=white)](https://www.python.org)
[![License: BSD-3-Clause](https://img.shields.io/badge/license-BSD--3--Clause-green)](LICENSE)
[![No Dependencies](https://img.shields.io/badge/dependencies-0-brightgreen)]()
[![marimo](https://marimo.io/shield.svg)](https://marimo.app/l/6fd0ic)

</div>

---

Browser notebooks can run JavaScript and WebAssembly, but they can't import arbitrary files from Python `site-packages`. Embedding the full Graphviz WASM bundle in every cell bloats your notebook. Loading from a CDN on every render breaks offline and locked-down environments.

`easydot` takes the middle path: it vendors [Graphviz WASM](https://github.com/hpcc-systems/hpcc-js-wasm), starts a tiny loopback asset server on demand, and lets notebook outputs reference a local URL. Small outputs. No manual setup. Works offline.

## Quick Start

```bash
uv add easydot
```

```python
import easydot

easydot.display("digraph { A -> B -> C }")
```

That's it. The return value has `_repr_html_()` and `_mime_()` methods, so it renders automatically as the last expression in a notebook cell.

## Source Modes

By default, `easydot` tries the local server first and falls back to a pinned CDN URL:

```python
easydot.display("digraph { A -> B }", source="auto")   # default
easydot.display("digraph { A -> B }", source="local")  # local only
easydot.display("digraph { A -> B }", source="cdn")    # CDN only
```

| Mode | Local server | CDN fallback | Best for |
|-------|:---:|:---:|---|
| `auto` | yes | yes | Most setups |
| `local` | yes | no | Air-gapped / offline environments |
| `cdn` | no | yes | Remote hosts where `127.0.0.1` isn't reachable from the browser |

To change the notebook-wide default without editing every display call, set
`EASYDOT_SOURCE` before rendering any graphs:

```python
import os

os.environ["EASYDOT_SOURCE"] = "cdn"
```

The environment variable accepts `auto`, `local`, or `cdn`. It only applies
when `source="auto"` is used, so explicit `source="local"` and `source="cdn"`
calls still win.

## marimo Support

`easydot` works with [marimo](https://marimo.io) out of the box. It detects marimo and uses its iframe display helper automatically, since marimo doesn't execute arbitrary inline scripts from plain `text/html` outputs. All source modes work.

Because of that script policy, `iframe=False` is not a marimo rendering mode. Use it only when embedding the generated HTML somewhere that already provides layout and executes script tags.

To inspect the bundled demo notebook from a checkout:

```bash
uv run marimo edit examples/demo.py
```

For a read-only local preview:

```bash
uv run marimo run examples/demo.py --headless --host 127.0.0.1 --port 2718 --no-token
```

Then open <http://localhost:2718>.

## Library Integration

For libraries that generate their own HTML, use the lower-level asset API:

```python
from easydot import asset_urls

js_url = asset_urls()["js"]
```

Then in your browser-side code:

```js
const mod = await import(jsUrl);
const graphviz = await mod.Graphviz.load();
const svg = graphviz.layout("digraph { A -> B }", "svg", "dot");
```

## CLI

`easydot` ships a small command-line tool:

```bash
# Render DOT to HTML on stdout
echo 'digraph { A -> B }' | easydot

# Print local asset server URLs
easydot --urls
```

## Runtime Model

The asset server is intentionally narrow:

- Binds only to `127.0.0.1`
- Uses an OS-assigned ephemeral port
- Serves only known packaged files (no directory browsing)
- Sets long-lived cache headers
- Shuts down automatically when the Python process exits

## What easydot Is Not

`easydot` does **not** call the system `dot` executable. All rendering happens client-side through WebAssembly. For server-side rendering to files, native Graphviz or the [`graphviz`](https://pypi.org/project/graphviz/) Python package may be a better fit.

## Licensing

The Python code is licensed under [BSD-3-Clause](LICENSE).

The vendored browser module (`src/easydot/assets/index.js`) comes from [`@hpcc-js/wasm-graphviz`](https://www.npmjs.com/package/@hpcc-js/wasm-graphviz), licensed under Apache-2.0. The upstream license is included at `src/easydot/assets/LICENSE.hpcc-js-wasm`; the pinned version lives in `src/easydot/_version.py`.

| Component | License |
|---|---|
| `easydot` Python code | BSD-3-Clause |
| Vendored Graphviz WASM | Apache-2.0 |
