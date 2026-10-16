"""Command-line interface for epicycles.

U0 scaffold: wires the three documented subcommands (``draw``, ``sweep``,
``info``) so that ``python -m epicycles --help`` works. Their options and
behavior are implemented in later work units; here they exist only as named
placeholders so the command surface is discoverable.
"""
from __future__ import annotations

import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="epicycles",
        description=(
            "Fourier-epicycle line drawing: input -> single closed path -> DFT "
            "-> animated chain of rotating vectors."
        ),
    )
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("draw", help="render an epicycle animation from a source")
    sub.add_parser(
        "sweep", help="render a grid of reconstructions for several term counts"
    )
    sub.add_parser(
        "info", help="print N, stroke count, connector length, and error table"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    parser.error(f"command '{args.command}' is not implemented yet")
    return 2  # unreachable: parser.error() exits with status 2


if __name__ == "__main__":
    raise SystemExit(main())
