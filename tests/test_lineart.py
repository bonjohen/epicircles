"""U13: raster line-art pipeline + AC-3.

Contract: load_gray -> binarize -> skeleton -> skeleton_to_strokes ->
join_strokes -> resample (N = next power of two >= tour points, capped 16384)
-> spectrum -> select. --kind auto picks lineart when Otsu ink fraction < 15%.
AC-3: at M=2048 every skeleton pixel is within 2px of the reconstruction, and
>=95% of reconstruction samples are within 2px of a skeleton pixel.
"""
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy.spatial import cKDTree

from epicycles.cli import detect_kind, next_pow2_capped, run_lineart_pipeline
from epicycles.core.fourier import evaluate
from epicycles.io.image import load_gray


def _two_circles(path):
    img = Image.new("L", (200, 120), 255)
    d = ImageDraw.Draw(img)
    d.ellipse([10, 30, 60, 80], outline=0, width=2)
    d.ellipse([130, 30, 180, 80], outline=0, width=2)
    img.save(path)


def _one_circle(path):
    img = Image.new("L", (200, 200), 255)
    ImageDraw.Draw(img).ellipse([30, 30, 170, 170], outline=0, width=2)
    img.save(path)


def test_next_pow2_capped():
    assert next_pow2_capped(1000) == 1024
    assert next_pow2_capped(1024) == 1024
    assert next_pow2_capped(1025) == 2048
    assert next_pow2_capped(20000) == 16384


def test_load_gray_downscales(tmp_path):
    p = tmp_path / "big.png"
    Image.new("L", (1600, 800), 255).save(p)
    g = load_gray(p, 400)
    assert max(g.shape) == 400


def test_two_disjoint_shapes_two_strokes_one_tour(tmp_path):
    p = tmp_path / "two.png"
    _two_circles(p)
    res = run_lineart_pipeline(str(p), "auto", 256, "magnitude")
    assert res.n_strokes == 2
    assert res.connector_len > 0
    assert len(res.z) == res.n


def test_kind_auto_picks_lineart(tmp_path):
    p = tmp_path / "line.png"
    _one_circle(p)
    assert detect_kind(str(p)) == "lineart"


def test_samples_auto_is_power_of_two_capped(tmp_path):
    p = tmp_path / "one.png"
    _one_circle(p)
    res = run_lineart_pipeline(str(p), "auto", 256, "magnitude")
    assert res.n <= 16384
    assert res.n & (res.n - 1) == 0  # power of two


def test_ac3_coverage_and_95_percent(tmp_path):
    p = tmp_path / "circle.png"
    _one_circle(p)
    res = run_lineart_pipeline(str(p), "auto", 2048, "magnitude")
    h = res.skel.shape[0]
    ys, xs = np.where(res.skel)
    skel_pts = np.column_stack([xs + 0.5, h - ys - 0.5])
    t = np.linspace(0, 1, 8192, endpoint=False)
    recon = evaluate(res.kept, t)
    recon_pts = np.column_stack([recon.real, recon.imag])

    recon_tree = cKDTree(recon_pts)
    skel_tree = cKDTree(skel_pts)
    # coverage: every skeleton pixel within 2px of the reconstruction
    d_skel_to_recon, _ = recon_tree.query(skel_pts)
    assert d_skel_to_recon.max() <= 2.0
    # >=95% of reconstruction samples within 2px of a skeleton pixel
    d_recon_to_skel, _ = skel_tree.query(recon_pts)
    assert (d_recon_to_skel <= 2.0).mean() >= 0.95
