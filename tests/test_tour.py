"""U8: join strokes into one closed tour.

Contract in docs/design.md#core/tour.py: greedy nearest-endpoint joining with
reversal; ties -> lowest index then forward; connector_len = sum of join gaps +
closing jump (last point -> first); a closed stroke (last==first within
1e-9*scale) drops the duplicate and contributes 0 closing length.
"""
import numpy as np

from epicycles.core.tour import join_strokes


def test_single_closed_stroke_drops_duplicate_connector_zero():
    s = np.array([0, 1, 1 + 1j, 1j, 0], dtype=np.complex128)  # last == first
    tour, conn = join_strokes([s])
    assert len(tour) == 4  # duplicate dropped
    assert conn == 0.0
    assert np.isclose(tour[0], 0)


def test_single_open_segment_connector_is_its_length():
    s = np.array([0, 3 + 4j], dtype=np.complex128)  # length 5
    tour, conn = join_strokes([s])
    assert len(tour) == 2
    assert np.isclose(conn, 5.0)  # closing jump back to start


def test_two_parallel_segments_joined_with_reversal():
    s0 = np.array([0, 10], dtype=np.complex128)
    s1 = np.array([1j, 10 + 1j], dtype=np.complex128)
    tour, conn = join_strokes([s0, s1])
    assert np.allclose(tour, [0, 10, 10 + 1j, 1j])
    assert np.isclose(conn, 2.0)  # join (1) + closing jump (1), exact


def test_deterministic_on_ties():
    a = np.array([-1, 0], dtype=np.complex128)
    b = np.array([1, 2], dtype=np.complex128)
    c = np.array([1j, 2j], dtype=np.complex128)
    t1, c1 = join_strokes([a, b, c])
    t2, c2 = join_strokes([a, b, c])
    assert np.array_equal(t1, t2) and c1 == c2
    # end of A is 0; B(start=1) and C(start=1j) tie at dist 1 -> lower index B.
    assert np.isclose(t1[2], 1)


def test_point_count_minus_dropped_duplicates():
    closed = np.array([0, 1, 1j, 0], dtype=np.complex128)  # 4 pts, 1 dropped
    open_ = np.array([5, 6], dtype=np.complex128)  # 2 pts
    tour, _ = join_strokes([closed, open_])
    assert len(tour) == (4 - 1) + 2
