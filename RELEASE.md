# Release

1. Set `version` in [`pyproject.toml`](./pyproject.toml) to the next release version.
1. If dependencies changed, refresh the lockfile:
   `uv lock`
1. Run the test suite:
   `uv run pytest`
1. Commit the release change.
1. Create and push a tag that matches the version, for example:
   `git tag v0.1.2`
   `git push origin v0.1.2`

Pushing the tag triggers the PyPI publish workflow on CI.

No `gh release create` step is needed for PyPI publishing with the current workflow.
