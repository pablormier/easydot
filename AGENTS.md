# AGENTS.md

- Keep changes minimal and scoped.
- Always use `uv` for Python testing and running commands.
- Run `uv run pytest` before finishing code changes when possible.
- Use `uv run marimo check examples/demo.py` to validate the demo notebook.
- Use `uv run marimo edit examples/demo.py` to debug the demo interactively.
- For a read-only local preview, use:
  `uv run marimo run examples/demo.py --headless --host 127.0.0.1 --port 2718 --no-token`
- `pyproject.toml` is the package version source of truth; `__version__` is derived from it.
- `UPSTREAM_VERSION` is only for the vendored Graphviz WASM dependency.
- Keep the library minimal. Prefer fail-fast behavior over defensive swallowing of errors.
- Do not add compatibility shims for older versions unless explicitly requested.
- Breaking changes are acceptable if they keep the codebase simpler and cleaner.
- For releases, follow [`RELEASE.md`](./RELEASE.md).
- Publish GitHub releases with `gh release create`, for example:
  `gh release create v0.1.0 --title v0.1.0 --notes "Initial release"`
- If a `gh release create` command fails because of permissions or sandboxing, rerun it with elevated privileges instead of changing the release flow.
