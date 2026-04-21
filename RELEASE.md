# Release

Never create or push a release tag until `main` is fully up to date with
`origin/main` and the release commit has already been pushed. Pushing a tag
triggers the PyPI publish workflow on CI, and PyPI files cannot be replaced.
Do not force-push or move a release tag after it has been pushed.

1. Start from `main` with a clean working tree:
   `git status --short --branch`
1. Fetch the latest remote state:
   `git fetch origin main --tags`
1. Confirm local `main` is not behind or diverged from `origin/main`:
   `git status --short --branch`
   The output must not show `behind` or `diverged`. If it does, integrate
   `origin/main` before changing the version. Do not tag from a branch that is
   behind `origin/main`.
1. Set `version` in [`pyproject.toml`](./pyproject.toml) to the next release
   version.
1. Refresh the lockfile so the editable package version matches:
   `uv lock`
1. Run the validation checks:
   `uv run pytest`
   `uv run marimo check examples/demo.py`
1. Commit the release change.
1. Push `main` first:
   `git push origin main`
1. Fetch and verify the pushed commit is still the remote tip:
   `git fetch origin main --tags`
   `git status --short --branch`
   The output must not show `ahead`, `behind`, or `diverged`.
1. Create and push a tag that matches the version only after `main` is synced:
   `git tag v0.1.2`
   `git push origin v0.1.2`
1. Create the GitHub release with `gh`, for example:
   `gh release create v0.1.2 --title v0.1.2 --notes "Release 0.1.2"`

If `gh release create` fails because the command needs elevated privileges, rerun it with the required privileges rather than changing the release process.
