# AGENTS.md

- Keep changes minimal and scoped.
- Always use `uv` for Python testing and running commands.
- Run `uv run pytest` before finishing code changes when possible.
- `pyproject.toml` is the package version source of truth; `__version__` is derived from it.
- `UPSTREAM_VERSION` is only for the vendored Graphviz WASM dependency.
- Keep the library minimal. Prefer fail-fast behavior over defensive swallowing of errors.
- Do not add compatibility shims for older versions unless explicitly requested.
- Breaking changes are acceptable if they keep the codebase simpler and cleaner.
- For releases, follow [`RELEASE.md`](./RELEASE.md).
