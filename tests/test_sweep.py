"""U10b: sweep grid. Assert on the traces handed to the plotter, not pixels."""
from pathlib import Path

import numpy as np

from epicycles.cli import main, run_svg_pipeline
from epicycles.core.fourier import evaluate, select
from epicycles.render.sweep import sweep_traces, write_sweep

FIX = Path(__file__).parent / "fixtures"


def test_sweep_traces_panel_count_and_data():
    full = run_svg_pipeline(str(FIX / "lineart_cc0.svg"), "auto", 512, "magnitude").full
    terms = [1, 4, 16, 64]
    traces = sweep_traces(full, terms, "magnitude", 500)
    assert [m for m, _ in traces] == terms
    t = np.linspace(0, 1, 500, endpoint=False)
    for m, z in traces:
        assert np.allclose(z, evaluate(select(full, m, "magnitude"), t))


def test_write_sweep_png(tmp_path):
    full = run_svg_pipeline(str(FIX / "circle.svg"), "auto", 64, "magnitude").full
    out = tmp_path / "grid.png"
    write_sweep(full, [1, 2, 4], out)
    assert out.exists() and out.stat().st_size > 0


def test_cli_sweep_writes_png(tmp_path):
    out = tmp_path / "g.png"
    rc = main(["sweep", str(FIX / "circle.svg"), "--terms", "1,4,16", "--out", str(out)])
    assert rc == 0
    assert out.exists() and out.stat().st_size > 0
