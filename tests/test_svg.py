"""U7: load SVG into strokes (y-up, transforms applied).

Contract in docs/design.md#io/svg.py: Document.paths() with transforms applied;
each continuous subpath -> one Stroke sampled at max(8, ceil(length*spu))
points; y negated (y_up = -y_svg); closed subpaths keep their closing point.
"""
from pathlib import Path

import numpy as np

from epicycles.io.svg import load_svg

FIX = Path(__file__).parent / "fixtures"


def test_circle_single_stroke_on_radius():
    strokes = load_svg(FIX / "circle.svg", 1.0)
    assert len(strokes) == 1
    z = strokes[0]
    center = 50 - 50j  # (cx, cy)=(50,50) in SVG -> y negated
    assert np.allclose(np.abs(z - center), 30.0, atol=1e-6 * 30.0)


def test_y_is_negated():
    # two_strokes: path0 at y_svg=0 (higher on screen), path1 at y_svg=5.
    s0, s1 = load_svg(FIX / "two_strokes.svg", 1.0)
    assert np.allclose(s0.imag, 0.0, atol=1e-9)
    assert np.allclose(s1.imag, -5.0, atol=1e-9)
    # higher on screen (path0) -> larger y_up
    assert s0.imag.mean() > s1.imag.mean()


def test_transform_applied():
    (s,) = load_svg(FIX / "transformed.svg", 1.0)
    # M0,0 L5,0 under translate(10,20) scale(2) -> (10,20),(20,20); y negated.
    assert np.isclose(s[0], 10 - 20j, atol=1e-6)
    assert np.isclose(s[-1], 20 - 20j, atol=1e-6)


def test_offset_viewbox_handled():
    (s,) = load_svg(FIX / "offset_viewbox.svg", 1.0)
    assert np.allclose(np.abs(s - 0j), 30.0, atol=1e-6 * 30.0)


def test_two_strokes_count():
    assert len(load_svg(FIX / "two_strokes.svg", 1.0)) == 2


def test_sample_count_budget_split():
    # two_strokes: 2 equal subpaths (len 10, total 20). budget 40 -> 20 each.
    s0, s1 = load_svg(FIX / "two_strokes.svg", 40)
    assert len(s0) == 20 and len(s1) == 20
    # tiny budget floors to the minimum of 8 per subpath.
    s0_min, _ = load_svg(FIX / "two_strokes.svg", 4)
    assert len(s0_min) == 8
    # single subpath gets the whole budget.
    (c,) = load_svg(FIX / "circle.svg", 200)
    assert len(c) == 200


def test_closed_subpath_keeps_closing_point():
    (c,) = load_svg(FIX / "circle.svg", 1.0)
    assert np.isclose(c[0], c[-1], atol=1e-6)
