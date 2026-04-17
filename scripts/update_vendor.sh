#!/usr/bin/env bash
# Download the latest (or a specific) version of @hpcc-js/wasm-graphviz
# and update the vendored assets + version references in easydot.
#
# Usage:
#   ./scripts/update_vendor.sh           # fetches latest from npm
#   ./scripts/update_vendor.sh 1.22.0    # fetches a specific version

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ASSETS_DIR="$REPO_ROOT/src/easydot/assets"
INIT_FILE="$REPO_ROOT/src/easydot/_version.py"
PACKAGE="@hpcc-js/wasm-graphviz"

# Resolve version ----------------------------------------------------------------

if [ $# -ge 1 ]; then
    VERSION="$1"
else
    VERSION="$(npm view "$PACKAGE" version)"
fi

CURRENT="$(grep 'UPSTREAM_VERSION' "$INIT_FILE" | head -1 | sed 's/.*"\(.*\)".*/\1/')"

if [ "$VERSION" = "$CURRENT" ]; then
    echo "Already at $VERSION — nothing to do."
    exit 0
fi

echo "Updating $PACKAGE: $CURRENT -> $VERSION"

# Download assets -----------------------------------------------------------------

TARBALL_URL="$(npm view "$PACKAGE@$VERSION" dist.tarball)"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

curl -sL "$TARBALL_URL" | tar xz -C "$TMPDIR"

EXTRACTED="$TMPDIR/package"

cp "$EXTRACTED/dist/index.js"      "$ASSETS_DIR/index.js"
cp "$EXTRACTED/LICENSE"            "$ASSETS_DIR/LICENSE.hpcc-js-wasm"
cp "$EXTRACTED/package.json"       "$ASSETS_DIR/package.json"
cp "$EXTRACTED/README.md"          "$ASSETS_DIR/README.hpcc-js-wasm.md"

# Update version in __init__.py ---------------------------------------------------

sed -i.bak "s/UPSTREAM_VERSION = \"$CURRENT\"/UPSTREAM_VERSION = \"$VERSION\"/" "$INIT_FILE"
rm -f "$INIT_FILE.bak"

echo "Done. Vendored assets updated to $PACKAGE@$VERSION."
echo "Review changes, run tests, then bump the easydot version in pyproject.toml if needed."
