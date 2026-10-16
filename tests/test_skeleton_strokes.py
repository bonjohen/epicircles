"""U12: skeleton_to_strokes — iterative DFS closed walk per component.

Contract in docs/design.md#core/raster.py: one stroke per 8-connected
component; DFS out-and-back over the spanning tree; start = lowest (row,col);
a tree of p pixels yields 2(p-1) points; final return to start not repeated;
pixel centre -> x=col+0.5, y=H-row-0.5; iterative (no RecursionError on a big
spiral).
"""
import numpy as np
from PIL import Image, ImageDraw

from epicycles.core.raster import binarize, skeleton, skeleton_to_strokes


def _t_skeleton():
    # T: horizontal row 0 cols 0..4 (5 px) + vertical col 2 rows 1..4 (4 px).
    m = np.zeros((6, 6), dtype=bool)
    m[0, 0:5] = True
    m[1:5, 2] = True
    return m  # tree of 9 pixels


def test_t_tree_point_count_is_2_p_minus_1():
    m = _t_skeleton()
    p = int(m.sum())
    (stroke,) = skeleton_to_strokes(m)
    assert len(stroke) == 2 * (p - 1)


def test_every_pixel_appears_in_walk():
    m = _t_skeleton()
    H = m.shape[0]
    (stroke,) = skeleton_to_strokes(m)
    walked = {(round(H - z.imag - 0.5), round(z.real - 0.5)) for z in stroke}
    pixels = set(zip(*[a.tolist() for a in np.where(m)]))
    assert walked == pixels


def test_consecutive_points_8_adjacent_and_closed():
    (stroke,) = skeleton_to_strokes(_t_skeleton())
    d = np.abs(np.diff(stroke))
    assert np.all(d <= np.sqrt(2) + 1e-9)
    assert abs(stroke[-1] - stroke[0]) <= np.sqrt(2) + 1e-9  # closed


def test_deterministic_start_and_pixel_centre_mapping():
    m = _t_skeleton()
    H = m.shape[0]
    (stroke,) = skeleton_to_strokes(m)
    # lowest (row,col) is (0,0) -> x=0.5, y=H-0.5
    assert np.isclose(stroke[0], 0.5 + 1j * (H - 0.5))


def test_big_spiral_no_recursion_error():
    H = W = 2000
    img = Image.new("L", (W, H), 255)
    d = ImageDraw.Draw(img)
    t = np.linspace(0, 1, 8000)
    theta = t * 30 * np.pi
    r = t * 900
    pts = [(1000 + ri * np.cos(a), 1000 + ri * np.sin(a)) for ri, a in zip(r, theta)]
    d.line(pts, fill=0, width=1)
    skel = skeleton(binarize(np.array(img, dtype=np.uint8), None))
    strokes = skeleton_to_strokes(skel)  # must not raise RecursionError
    assert sum(len(s) for s in strokes) > 0
