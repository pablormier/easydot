"""Command-line helpers for easydot."""

from __future__ import annotations

import argparse
import sys

from easydot import asset_urls, html


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render Graphviz DOT with browser-side WASM helpers.")
    parser.add_argument("dot", nargs="?", help="DOT source. Reads stdin when omitted.")
    parser.add_argument("--engine", default="dot", help="Graphviz layout engine.")
    parser.add_argument("--urls", action="store_true", help="Print local asset URLs instead of HTML.")
    args = parser.parse_args(argv)

    if args.urls:
        for key, value in asset_urls().items():
            print(f"{key}: {value}")
        return 0

    dot = args.dot if args.dot is not None else sys.stdin.read()
    print(html(dot, engine=args.engine))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
