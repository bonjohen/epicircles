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


def test_revealed_count_never_leads_the_pen():
    """F8.1: on frame i the last revealed trail point lies at t in [t_i - 1/R, t_i]."""
    from epicycles.render.frames import revealed_count

    for n_frames, R in [(10, 100), (150, 4096), (7, 3), (600, 16384)]:
        prev = 0
        for i in range(n_frames):
            k = revealed_count(i, n_frames, R)
            assert 1 <= k <= R
            assert k >= prev
            prev = k
            t_last = (k - 1) / R
            t_i = i / n_frames
            assert t_i - 1 / R - 1e-12 <= t_last <= t_i + 1e-12


def test_write_animation_reveal_uses_revealed_count(monkeypatch, tmp_path):
    """F8.2: write_animation's reveal goes through frames.revealed_count."""
    import numpy as np
    from epicycles.core.fourier import select, spectrum
    from epicycles.render import animate

    calls = []
    real = animate.revealed_count

    def spy(i, n, r):
        calls.append((i, n, r))
        return real(i, n, r)

    monkeypatch.setattr(animate, "revealed_count", spy)
    z = np.exp(2j * np.pi * np.arange(64) / 64)
    kept = select(spectrum(z), 3, "magnitude")
    animate.write_animation(kept, tmp_path / "a.gif", n_frames=5, fps=5)
    assert sorted(set(c[0] for c in calls if c[1] == 5)) == list(range(5))
