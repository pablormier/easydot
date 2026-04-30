"""Command-line helpers for easydot."""

from __future__ import annotations

import argparse
import sys

import easydot
from easydot import asset_urls


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render Graphviz DOT with browser-side WASM helpers.")
    parser.add_argument("dot", nargs="?", help="DOT source. Reads stdin when omitted.")
    parser.add_argument(
        "--backend",
        choices=("auto", "browser", "wasm", "native"),
        default="browser",
        help="Rendering backend.",
    )
    parser.add_argument("--engine", default="dot", help="Graphviz layout engine.")
    parser.add_argument(
        "--format",
        choices=("html", "svg", "png", "pdf"),
        default="html",
        help="Output format. 'html' (default) produces display-ready HTML; 'svg' produces a raw SVG string; 'png'/'pdf' require --backend native.",
    )
    parser.add_argument(
        "--fit",
        choices=("none", "horizontal", "vertical", "both"),
        default="none",
        help="Fit mode for HTML output (only used with --format html).",
    )
    parser.add_argument(
        "--scale",
        type=float,
        default=1.0,
        help="Scale factor for HTML output (only used with --format html).",
    )
    parser.add_argument("--urls", action="store_true", help="Print local asset URLs instead of HTML.")
    args = parser.parse_args(argv)

    if args.urls:
        for key, value in asset_urls().items():
            print(f"{key}: {value}")
        return 0

    dot = args.dot if args.dot is not None else sys.stdin.read()

    if args.format == "html":
        print(easydot.html(dot, backend=args.backend, engine=args.engine, fit=args.fit, scale=args.scale))
        return 0

    if args.format == "svg":
        if args.backend == "browser":
            print(
                "error: --format svg is not supported with --backend browser. "
                "Use --backend wasm, --backend native, or --backend auto.",
                file=sys.stderr,
            )
            return 1
        print(easydot.svg(dot, backend=args.backend, engine=args.engine))
        return 0

    if args.format in ("png", "pdf"):
        if args.backend in ("browser", "wasm"):
            print(
                f"error: --format {args.format} requires --backend native.",
                file=sys.stderr,
            )
            return 1
        backend = "native" if args.backend == "auto" else args.backend
        result = easydot.native(dot, engine=args.engine, format=args.format)
        if isinstance(result, bytes):
            sys.stdout.buffer.write(result)
        else:
            sys.stdout.write(result)
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
