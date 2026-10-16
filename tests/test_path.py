"""U4: arc-length resampling of a closed tour.

Contracts in docs/design.md#core/path.py:
  arc_length(tour) -> (n+1,) cumulative length incl. closing segment, [0]=0.
  resample(tour, n) -> n points uniform in arc length, starting at tour[0];
    raises ValueError if total length == 0.
"""
import numpy as np
import pytest

from epicycles.core.path import arc_length, resample

SQUARE = np.array([0, 1, 1 + 1j, 1j], dtype=np.complex128)


def test_square_perimeter_is_four():
    cum = arc_length(SQUARE)
    assert cum.shape == (5,)
    assert cum[0] == 0.0
    assert np.isclose(cum[-1], 4.0)


def test_resample_square_corners_and_midpoints():
    got = resample(SQUARE, 8)
    expect = np.array(
        [0, 0.5, 1, 1 + 0.5j, 1 + 1j, 0.5 + 1j, 1j, 0.5j], dtype=np.complex128
    )
    assert np.allclose(got, expect, atol=1e-9)


def test_resample_spacing_uniform():
    n = 64
    got = resample(SQUARE, n)
    closed = np.concatenate([got, got[:1]])
    seg = np.abs(np.diff(closed))
    assert np.allclose(seg, 4.0 / n, atol=1e-9)


def test_first_point_preserved():
    got = resample(SQUARE, 13)
    assert np.isclose(got[0], SQUARE[0], atol=1e-12)


def test_zero_length_raises():
    degenerate = np.full(5, 2 + 1j, dtype=np.complex128)
    with pytest.raises(ValueError):
        resample(degenerate, 8)
