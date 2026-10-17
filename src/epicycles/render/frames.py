"""Per-frame epicycle geometry (pure; no plotting).

For a selected spectrum, each frame at parameter ``t_j = j/n_frames`` yields the
circle centres, their radii, and the pen position. ``centers = chain[:-1]`` are
the moving circle centres; ``radii = |c|`` of terms ``1..m-1`` in selection
order (constant across frames); ``pen = chain[-1]``.
"""
from __future__ import annotations

from typing import NamedTuple

import numpy as np

from epicycles.core.fourier import Spectrum, chain, evaluate
from epicycles.core.tour import PEN_UP


def trail_resolution(n_terms: int, n_samples: int = 0) -> int:
    """Dense-trail point count: ``max(8·n_terms, n_samples, 2)``.

    Independent of ``n_frames`` — the pen trail's smoothness is set by the term
    count (and the drawing's sample count), not the animation's frame count.
    """
    return max(8 * int(n_terms), int(n_samples), 2)


def revealed_count(i: int, n_frames: int, resolution: int) -> int:
    """Dense-trail points to show on frame ``i``: ``min(R, floor(i*R/n_frames) + 1)``.

    The last revealed point is at ``t <= t_i = i/n_frames``, so the trail never
    runs ahead of the pen tip (F8.1).
    """
    return min(int(resolution), (int(i) * int(resolution)) // int(n_frames) + 1)


def pen_path(spec: Spectrum, resolution: int) -> np.ndarray:
    """Dense pen trajectory: ``evaluate(spec, arange(R)/R)``, shape ``(R,)``."""
    t = np.arange(resolution) / resolution
    return evaluate(spec, t)


def trail_labels(label: np.ndarray, resolution: int) -> np.ndarray:
    """Label for each of ``resolution`` dense pen-trail points.

    Trail point ``r`` (at ``t = r/R``) carries the label of sample ``⌊t·N⌋``
    (FR-11), where ``N = len(label)``. Returns ``int16 (resolution,)``. Lets the
    renderer skip ``PEN_UP`` runs on the dense trail.
    """
    label = np.asarray(label, dtype=np.int16)
    n = label.shape[0]
    r = np.arange(int(resolution))
    return label[(r * n) // int(resolution)]


def break_pen_up(pen: np.ndarray, labels: np.ndarray) -> np.ndarray:
    """Dense pen trail with ``PEN_UP`` points set to NaN (so they aren't drawn).

    ``pen`` is the ``(R,)`` dense trajectory; ``labels`` the ``(N,)`` per-sample
    tour labels. Returns a complex copy where every trail point whose
    :func:`trail_labels` value is ``PEN_UP`` is ``nan+nanj`` — matplotlib leaves
    a gap there (the arm still moves, the pen lifts).
    """
    out = np.asarray(pen, dtype=np.complex128).copy()
    out[trail_labels(labels, out.shape[0]) == PEN_UP] = np.nan + 1j * np.nan
    return out


class FrameGeom(NamedTuple):
    centers: np.ndarray  # complex128, shape (m-1,)
    radii: np.ndarray  # float64, shape (m-1,)
    pen: complex


def frame_geometry(spec: Spectrum, n_frames: int) -> list[FrameGeom]:
    """Return one :class:`FrameGeom` per frame, ``t_j = j/n_frames``."""
    radii = np.abs(spec.c[1:])
    frames: list[FrameGeom] = []
    for j in range(n_frames):
        ch = chain(spec, j / n_frames)
        frames.append(FrameGeom(ch[:-1], radii, complex(ch[-1])))
    return frames
