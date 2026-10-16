"""U17 (P5): two_opt stroke-order improvement.

Contract in docs/design.md#core/tour.py: order is a list of (index, reversed)
pairs; two_opt applies strictly-improving cyclic 2-opt moves, so the connector
length never increases and the result is deterministic.
"""
import numpy as np

from epicycles.core.tour import order_connector_length, two_opt


def _corner_strokes():
    # Degenerate point-strokes at the four corners of a 10x10 square.
    corners = [0, 10, 10 + 10j, 10j]
    return [np.array([c, c], dtype=np.complex128) for c in corners]


def test_two_opt_uncrosses_and_reaches_perimeter():
    strokes = _corner_strokes()
    crossing = [(0, False), (2, False), (1, False), (3, False)]
    c0 = order_connector_length(strokes, crossing)
    opt = two_opt(strokes, crossing)
    c1 = order_connector_length(strokes, opt)
    assert c1 <= c0 + 1e-12
    assert c1 < c0  # the crossing order is improvable
    assert np.isclose(c1, 40.0)  # square perimeter


def test_two_opt_deterministic():
    strokes = _corner_strokes()
    crossing = [(0, False), (2, False), (1, False), (3, False)]
    assert two_opt(strokes, crossing) == two_opt(strokes, crossing)


def test_two_opt_never_increases_on_optimal():
    strokes = _corner_strokes()
    good = [(0, False), (1, False), (2, False), (3, False)]
    c0 = order_connector_length(strokes, good)
    opt = two_opt(strokes, good)
    assert order_connector_length(strokes, opt) <= c0 + 1e-12
