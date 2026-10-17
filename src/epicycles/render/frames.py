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


def trail_resolution(n_terms: int, n_samples: int = 0) -> int:
    """Dense-trail point count: ``max(8·n_terms, n_samples, 2)``.

    Independent of ``n_frames`` — the pen trail's smoothness is set by the term
    count (and the drawing's sample count), not the animation's frame count.
    """
    return max(8 * int(n_terms), int(n_samples), 2)


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
