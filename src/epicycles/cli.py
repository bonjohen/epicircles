"""Command-line interface for epicycles.

``draw`` and ``info`` are wired for SVG input (U10): fetch -> load_svg ->
join_strokes -> resample -> spectrum -> select, then animate / export / report.
Raster (lineart) and photo inputs are added in later units.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from epicycles.core.fourier import Spectrum, error, select, spectrum
from epicycles.core.path import resample
from epicycles.core.tour import join_strokes
from epicycles.io.export import to_json
from epicycles.io.fetch import fetch
from epicycles.io.svg import load_svg

_DEFAULT_CACHE = Path(".cache")
_SVG_SAMPLES = 2048


@dataclass
class SvgResult:
    z: np.ndarray
    full: Spectrum
    kept: Spectrum
    n_strokes: int
    connector_len: float
    n: int
    order: str


def run_svg_pipeline(
    src: str,
    samples: str | int,
    terms: int,
    order: str,
    samples_per_unit: float = 1.0,
    cache_dir: Path = _DEFAULT_CACHE,
) -> SvgResult:
    """Run the SVG path of the pipeline and return the specs and metadata."""
    path = fetch(src, cache_dir)
    strokes = load_svg(path, samples_per_unit)
    tour, connector_len = join_strokes(strokes)
    n = _SVG_SAMPLES if samples == "auto" else int(samples)
    z = resample(tour, n)
    full = spectrum(z)
    kept = select(full, terms, order)
    return SvgResult(z, full, kept, len(strokes), connector_len, n, order)


def _kind_for(src: str, kind: str) -> str:
    if kind != "auto":
        return kind
    return "svg" if src.lower().endswith(".svg") else "raster"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="epicycles",
        description=(
            "Fourier-epicycle line drawing: input -> single closed path -> DFT "
            "-> animated chain of rotating vectors."
        ),
    )
    sub = parser.add_subparsers(dest="command")

    draw = sub.add_parser("draw", help="render an epicycle animation from a source")
    draw.add_argument("src")
    draw.add_argument("--kind", choices=["auto", "svg", "lineart", "photo"], default="auto")
    draw.add_argument("--samples", default="auto")
    draw.add_argument("--terms", type=int, default=256)
    draw.add_argument("--order", choices=["magnitude", "frequency"], default="magnitude")
    draw.add_argument("--frames", type=int, default=600)
    draw.add_argument("--fps", type=int, default=30)
    draw.add_argument("--json", dest="json_path", default=None)
    draw.add_argument("--out", dest="out_path", default=None)

    info = sub.add_parser("info", help="print N, stroke count, connector length, error table")
    info.add_argument("src")
    info.add_argument("--kind", choices=["auto", "svg", "lineart", "photo"], default="auto")
    info.add_argument("--samples", default="auto")
    info.add_argument("--terms", type=int, default=256)
    info.add_argument("--order", choices=["magnitude", "frequency"], default="magnitude")

    sub.add_parser("sweep", help="render a grid of reconstructions for several term counts")
    return parser


def _require_svg(src: str, kind: str) -> None:
    if _kind_for(src, kind) != "svg":
        raise NotImplementedError(
            "only SVG input is implemented so far; raster/photo arrive in later units"
        )


def _cmd_draw(args: argparse.Namespace) -> int:
    _require_svg(args.src, args.kind)
    res = run_svg_pipeline(args.src, args.samples, args.terms, args.order)
    rep = error(res.z, res.full, res.kept)
    print(
        f"N={res.n} strokes={res.n_strokes} connector_len={res.connector_len:.6g} "
        f"terms={args.terms} rms={rep.rms_sampled:.6g} error={rep.pct_height:.4g}%"
    )
    if args.json_path is not None:
        Path(args.json_path).write_text(to_json(res.kept, res.n, res.order))
    if args.out_path is not None:
        from epicycles.render.animate import write_animation

        write_animation(res.kept, args.out_path, args.frames, args.fps, original=res.z)
    return 0


def _cmd_info(args: argparse.Namespace) -> int:
    _require_svg(args.src, args.kind)
    res = run_svg_pipeline(args.src, args.samples, args.terms, args.order)
    rep = error(res.z, res.full, res.kept)
    print(f"N:                {res.n}")
    print(f"strokes:          {res.n_strokes}")
    print(f"connector length: {res.connector_len:.6g}")
    print(f"terms (M):        {args.terms} ({res.order})")
    print(f"rms (sampled):    {rep.rms_sampled:.6g}")
    print(f"rms (Parseval):   {rep.rms_parseval:.6g}")
    print(f"error:            {rep.pct_height:.4g}% of max(width, height)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    if args.command == "draw":
        return _cmd_draw(args)
    if args.command == "info":
        return _cmd_info(args)
    parser.error(f"command '{args.command}' is not implemented yet")
    return 2  # unreachable: parser.error() exits with status 2


if __name__ == "__main__":
    raise SystemExit(main())
