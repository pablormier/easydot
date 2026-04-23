# AGENTS.md

- Keep changes minimal and scoped.
- Always use `uv` for Python testing and running commands.
- Run `uv run pytest` before finishing code changes when possible.
- Use `uv run marimo check examples/demo.py` to validate the demo notebook.
- Use `uv run marimo edit examples/demo.py` to debug the demo interactively.
- For a read-only local preview, use:
  `uv run marimo run examples/demo.py --headless --host 127.0.0.1 --port 2718 --no-token`
- When browser behavior matters and Playwright MCP is available, validate against the
  local marimo preview:
  1. Start the preview with the command above.
  2. Open `http://127.0.0.1:2718` with Playwright MCP.
  3. Use viewport resizing plus DOM measurements to verify layout-sensitive behavior
     such as iframe heights, SVG dimensions, scrolling, and fit modes.
  4. Prefer `browser_evaluate` for precise measurements and `browser_snapshot` or
     screenshots only when visual context is needed.
  5. Stop the preview server when finished.
- If Playwright MCP reports an artifact directory error such as trying to create
  `/.playwright-mcp`, continue with DOM/browser checks if the session is usable;
  otherwise report that the MCP output directory needs reconfiguration.
- In notebook frontends, do not auto-select marimo-specific iframe wrappers
  unless a marimo runtime is actually active. Preserve IPython/VS Code rich-display
  behavior unless the change is explicitly validated there.
- `pyproject.toml` is the package version source of truth; `__version__` is derived from it.
- `UPSTREAM_VERSION` is only for the vendored Graphviz WASM dependency.
- Keep the library minimal. Prefer fail-fast behavior over defensive swallowing of errors.
- Do not add compatibility shims for older versions unless explicitly requested.
- Breaking changes are acceptable if they keep the codebase simpler and cleaner.
- For releases, follow [`RELEASE.md`](./RELEASE.md).
- Publish GitHub releases with `gh release create`, for example:
  `gh release create v0.1.0 --title v0.1.0 --notes "Initial release"`
- If a `gh release create` command fails because of permissions or sandboxing, rerun it with elevated privileges instead of changing the release flow.
