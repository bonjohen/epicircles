"""U18 (P5): Euler stroke extraction reduces retracing.

Contract: skeleton_to_strokes_euler traverses an Eulerian component (all even
degree, e.g. a closed loop) once per edge; non-Eulerian components fall back to
the DFS walk. Total walk length is never longer than the DFS walk.
"""
import numpy as np

from epicycles.core.raster import skeleton_to_strokes, skeleton_to_strokes_euler


def _closed_length(strokes):
    return sum(
        float(np.abs(np.diff(s)).sum() + abs(s[-1] - s[0])) for s in strokes
    )


def _square_ring():
    m = np.zeros((20, 20), dtype=bool)
    m[5, 5:15] = True
    m[14, 5:15] = True
    m[5:15, 5] = True
    m[5:15, 14] = True
    return m  # 1px closed loop -> every pixel degree 2 (Eulerian)


def test_euler_loop_not_longer_than_dfs():
    m = _square_ring()
    dfs = skeleton_to_strokes(m)
    eul = skeleton_to_strokes_euler(m)
    assert _closed_length(eul) <= _closed_length(dfs) + 1e-9
    assert _closed_length(eul) < _closed_length(dfs)  # a loop is traced once, not twice


def test_euler_visits_each_loop_pixel_once():
    m = _square_ring()
    (stroke,) = skeleton_to_strokes_euler(m)
    assert len(stroke) == int(m.sum())  # one point per pixel, no retrace


def test_euler_tree_fallback_not_longer_than_dfs():
    # A "T" has odd-degree vertices -> falls back to DFS -> equal length.
    m = np.zeros((6, 6), dtype=bool)
    m[0, 0:5] = True
    m[1:5, 2] = True
    dfs = skeleton_to_strokes(m)
    eul = skeleton_to_strokes_euler(m)
    assert _closed_length(eul) <= _closed_length(dfs) + 1e-9
