"""U10: SVG pipeline via the CLI, plus AC-1b and AC-2.

Asserts on produced files and on spectrum/error data — never on pixels.
"""
import json
from pathlib import Path

import numpy as np
from PIL import Image

from epicycles.cli import main, run_svg_pipeline
from epicycles.core.fourier import error

FIX = Path(__file__).parent / "fixtures"


def test_draw_svg_produces_gif_and_json(tmp_path):
    out = tmp_path / "out.gif"
    coeffs = tmp_path / "c.json"
    rc = main(
        [
            "draw",
            str(FIX / "circle.svg"),
            "--terms",
            "3",
            "--frames",
            "6",
            "--fps",
            "10",
            "--out",
            str(out),
            "--json",
            str(coeffs),
        ]
    )
    assert rc == 0
    assert out.exists() and out.stat().st_size > 0
    with Image.open(out) as im:
        assert getattr(im, "n_frames", 1) == 6
    obj = json.loads(coeffs.read_text())
    assert set(obj) == {"N", "ordering", "terms"}
    assert len(obj["terms"]) == 3


def test_info_prints_error_table(tmp_path, capsys):
    rc = main(["info", str(FIX / "circle.svg"), "--terms", "16"])
    assert rc == 0
    out = capsys.readouterr().out.lower()
    assert "connector" in out
    assert "rms" in out or "error" in out


def test_ac1b_circle_pipeline_single_harmonic():
    # Full spectrum of the resampled <circle> r=30: excluding k=0, the |k|=1
    # term equals r within 1e-3*r and every other term is below 1e-3*r.
    res = run_svg_pipeline(str(FIX / "circle.svg"), "auto", 256, "magnitude")
    k, c = res.full
    r = 30.0
    nonzero = k != 0
    mags = np.abs(c)
    k1 = mags[np.abs(k) == 1].max()
    assert abs(k1 - r) < 1e-3 * r
    other = mags[nonzero & (np.abs(k) != 1)]
    assert np.all(other < 1e-3 * r)


def test_ac2_synthetic_smoke_under_half_percent():
    # Synthetic few-harmonic curve: a fast smoke test (converges almost at once).
    res = run_svg_pipeline(str(FIX / "lineart_cc0.svg"), "auto", 512, "magnitude")
    rep = error(res.z, res.full, res.kept)
    assert rep.pct_height < 0.5


def test_ac2_real_lineart_under_half_percent():
    # AC-2 proper: a real public-domain multi-stroke web drawing (ethanol_pd.svg).
    res = run_svg_pipeline(str(FIX / "ethanol_pd.svg"), "auto", 512, "magnitude")
    assert res.n_strokes >= 2  # genuinely multi-stroke
    rep = error(res.z, res.full, res.kept)
    assert rep.pct_height < 0.5


def _scaled_svg(tmp_path, s):
    d = "M0,0 L3,1 L1,4 L5,5 L2,7 L0,3"
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1000">'
        f'<g transform="scale({s})"><path d="{d}"/></g></svg>'
    )
    p = tmp_path / f"scaled_{s}.svg"
    p.write_text(svg)
    return p


def test_sampling_is_scale_invariant(tmp_path):
    # F2.2: the same drawing at x0.01 and x100 gives the same %-error.
    errs = {}
    for s in (0.01, 100.0):
        res = run_svg_pipeline(str(_scaled_svg(tmp_path, s)), 512, 64, "magnitude")
        errs[s] = error(res.z, res.full, res.kept).pct_height
    assert abs(errs[0.01] - errs[100.0]) < 1e-6
