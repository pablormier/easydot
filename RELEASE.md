# Release

Releases are automated from `main`:

1. Use a conventional commit prefix for releasable changes such as `fix:`,
   `feat:`, `deps:`, or `docs:`. A `BREAKING CHANGE:` footer requests a major
   release.
2. The CI workflow runs tests, validates `examples/demo.py`, and builds a
   distribution on every pull request and push to `main`.
3. Release Please opens a release PR after releasable commits reach `main`.
   Its merge updates the version and changelog, creates the matching `v*` tag,
   and publishes a GitHub release.
4. The publication workflow validates the release tag with the same CI checks.
   Only after those checks pass does it build and publish the distributions to
   PyPI.

Do not create or move release tags manually. If a publication needs to be
retried, run the `Publish to PyPI` workflow manually and provide the existing
release tag. PyPI trusted publishing must be configured for the `pypi`
environment.
