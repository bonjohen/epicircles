"""F7.1: the GIF pen trail is sampled densely, not once per frame.

A high-term curve must not degrade into an ``n_frames``-sided polygon. These
assert on the trail *data* (point count and endpoint), never on pixels.
"""
import numpy as np

from epicycles.core.fourier import evaluate, select, spectrum
from epicycles.render.frames import pen_path, trail_resolution


def _spec(n=64, m=24):
    j = np.arange(n)
    z = np.exp(2j * np.pi * j / n) + 0.3 * np.exp(2j * np.pi * 5 * j / n)
    return select(spectrum(z), m, "magnitude")


def test_trail_resolution_independent_of_n_frames():
    spec = _spec()
    m = len(spec.c)
    # trail_resolution takes no n_frames argument: resolution is fixed by terms.
    assert trail_resolution(m, 0) == max(8 * m, 2)
    assert trail_resolution(m, 500) == max(8 * m, 500)
    # far denser than a typical small frame count
    assert trail_resolution(m, 0) >= 8 * m


def test_pen_path_is_dense_and_matches_evaluate():
    spec = _spec()
    r = trail_resolution(len(spec.c), 0)
    path = pen_path(spec, r)
    assert path.shape == (r,)
    # the dense trail IS the reconstruction sampled at t=i/R
    t = np.arange(r) / r
    assert np.allclose(path, evaluate(spec, t))
