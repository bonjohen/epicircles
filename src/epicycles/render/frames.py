"""Per-frame epicycle geometry (pure; no plotting).

For a selected spectrum, each frame at parameter ``t_j = j/n_frames`` yields the
circle centres, their radii, and the pen position. ``centers = chain[:-1]`` are
the moving circle centres; ``radii = |c|`` of terms ``1..m-1`` in selection
order (constant across frames); ``pen = chain[-1]``.
"""
from __future__ import annotations

from typing import NamedTuple

import numpy as np

from epicycles.core.fourier import Spectrum, chain


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
