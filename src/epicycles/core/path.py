"""Arc-length geometry on a closed complex tour.

A ``Tour`` is a closed polyline stored as ``np.ndarray[complex128]`` shape
``(n,)``: the last point connects back to the first, and the first point is not
repeated at the end. Resampling uniformly in arc length makes a path's Fourier
coefficients depend on geometry alone (constant pen speed).
"""
from __future__ import annotations

import numpy as np


def arc_length(tour: np.ndarray) -> np.ndarray:
    """Cumulative arc length along the closed tour, including the closing segment.

    Returns shape ``(n+1,)`` with ``[0] == 0`` and ``[-1]`` the full perimeter
    (the jump from the last point back to the first included).
    """
    tour = np.asarray(tour, dtype=np.complex128)
    closed = np.concatenate([tour, tour[:1]])
    seg = np.abs(np.diff(closed))
    return np.concatenate([[0.0], np.cumsum(seg)])


def resample(tour: np.ndarray, n: int) -> np.ndarray:
    """Return ``n`` points spaced uniformly in arc length, starting at ``tour[0]``.

    Raises :class:`ValueError` if the tour has zero total length.
    """
    tour = np.asarray(tour, dtype=np.complex128)
    cum = arc_length(tour)
    total = float(cum[-1])
    if total == 0.0:
        raise ValueError("cannot resample a zero-length tour")
    s = np.arange(n) / n * total  # [0, total), so s[0]=0 -> tour[0]
    closed = np.concatenate([tour, tour[:1]])
    re = np.interp(s, cum, closed.real)
    im = np.interp(s, cum, closed.imag)
    return (re + 1j * im).astype(np.complex128)
