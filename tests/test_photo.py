"""U16: photo pipeline (edges -> skeleton -> prune -> strokes) + CLI wiring.

AC-4 (recognizable animation from a real photo) and AC-5 (URL end-to-end) are
manual, since the test suite is offline. Here we test kind auto-detection on a
synthetic photo-like image and the photo pipeline on a synthetic edged shape.
"""
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from epicycles.cli import detect_kind, main, run_photo_pipeline


def test_detect_kind_photo(tmp_path):
    rng = np.random.default_rng(1)
    img = (rng.random((120, 160)) * 255).astype(np.uint8)  # dense -> ink >= 15%
    p = tmp_path / "noise.png"
    Image.fromarray(img, "L").save(p)
    assert detect_kind(str(p)) == "photo"


def test_run_photo_pipeline_on_disk(tmp_path):
    img = Image.new("L", (160, 160), 40)
    ImageDraw.Draw(img).ellipse([40, 40, 120, 120], fill=220)  # edge ring
    p = tmp_path / "disk.png"
    img.save(p)
    res = run_photo_pipeline(
        str(p), "auto", 256, "magnitude",
        sigma=2.0, low=0.1, high=0.2, min_component=5, spur=3,
    )
    assert res.n_strokes >= 1
    assert len(res.z) == res.n
    assert res.n & (res.n - 1) == 0  # power of two


def test_cli_draw_photo_writes_files(tmp_path):
    img = Image.new("L", (120, 120), 40)
    ImageDraw.Draw(img).ellipse([30, 30, 90, 90], fill=220)
    p = tmp_path / "d.png"
    img.save(p)
    out = tmp_path / "o.gif"
    js = tmp_path / "c.json"
    rc = main(
        [
            "draw", str(p), "--kind", "photo", "--terms", "8",
            "--frames", "4", "--fps", "8", "--sigma", "2.0",
            "--out", str(out), "--json", str(js),
        ]
    )
    assert rc == 0
    assert out.exists() and js.exists()
