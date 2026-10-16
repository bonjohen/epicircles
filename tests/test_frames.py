"""U9: per-frame geometry (pure).

Contract in docs/design.md#render: frame_geometry(spec, n_frames) ->
list[FrameGeom] where centers = chain[:-1], radii = |c| of terms 1..m-1 in
selection order, pen = chain[-1]; t_j = j/n_frames.
"""
import numpy as np

from epicycles.core.fourier import evaluate, select, spectrum
from epicycles.render.frames import FrameGeom, frame_geometry


def _spec(n=32, m=6):
    j = np.arange(n)
    z = (
        (1 - 1j)
        + 2.0 * np.exp(2j * np.pi * j / n)
        + 0.7 * np.exp(-4j * np.pi * j / n)
        + 0.3 * np.exp(6j * np.pi * j / n)
    )
    return select(spectrum(z), m, "magnitude")


def test_frame_count_matches_n_frames():
    assert len(frame_geometry(_spec(), 120)) == 120


def test_frame0_pen_equals_evaluate_at_zero():
    spec = _spec()
    g0 = frame_geometry(spec, 60)[0]
    assert isinstance(g0, FrameGeom)
    assert np.isclose(g0.pen, evaluate(spec, np.array([0.0]))[0], atol=1e-12)


def test_centers_and_radii_length_m_minus_1():
    spec = _spec(m=6)
    g = frame_geometry(spec, 10)[3]
    assert len(g.centers) == 5
    assert len(g.radii) == 5


def test_radii_in_selection_order():
    spec = _spec(m=6)
    g = frame_geometry(spec, 10)[0]
    assert np.allclose(g.radii, np.abs(spec.c[1:]))
