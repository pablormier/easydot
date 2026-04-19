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
1. Create the GitHub release with `gh`, for example:
   `gh release create v0.1.2 --title v0.1.2 --notes "Release 0.1.2"`

Pushing the tag triggers the PyPI publish workflow on CI.

If `gh release create` fails because the command needs elevated privileges, rerun it with the required privileges rather than changing the release process.
