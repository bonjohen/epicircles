"""U7: load SVG into strokes (y-up, transforms applied).

Contract in docs/design.md#io/svg.py: Document.paths() with transforms applied;
each continuous subpath -> one Stroke sampled at max(8, ceil(length*spu))
points; y negated (y_up = -y_svg); closed subpaths keep their closing point.
"""
import math
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


def test_sample_count_rule():
    # two_strokes segment length = 10. spu=2.0 -> ceil(20)=20 points.
    s0, _ = load_svg(FIX / "two_strokes.svg", 2.0)
    assert len(s0) == 20
    # tiny spu floors to the minimum of 8.
    s0_min, _ = load_svg(FIX / "two_strokes.svg", 0.01)
    assert len(s0_min) == 8
    # circle: length 2*pi*30, spu=1.0 -> ceil(188.4956)=189.
    (c,) = load_svg(FIX / "circle.svg", 1.0)
    assert len(c) == max(8, math.ceil(2 * math.pi * 30 * 1.0))


def test_closed_subpath_keeps_closing_point():
    (c,) = load_svg(FIX / "circle.svg", 1.0)
    assert np.isclose(c[0], c[-1], atol=1e-6)
