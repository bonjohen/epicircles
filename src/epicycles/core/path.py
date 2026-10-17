"""Arc-length geometry on a closed complex tour.

A ``Tour`` is a closed polyline stored as ``np.ndarray[complex128]`` shape
``(n,)``: the last point connects back to the first, and the first point is not
repeated at the end. Resampling uniformly in arc length makes a path's Fourier
coefficients depend on geometry alone (constant pen speed).
"""
from __future__ import annotations

import numpy as np

from epicycles.core.tour import PEN_UP


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


def resample_labeled(
    z: np.ndarray, seg_label: np.ndarray, n: int, jump_time: float = 0.0
) -> tuple[np.ndarray, np.ndarray]:
    """Resample a labelled tour in **parameter time**, with smooth pen-up jumps.

    Each pen-up segment (``seg_label == PEN_UP``) gets a fixed ``jump_time``
    fraction of the period; the remaining time is split among pen-down segments
    in proportion to arc length (constant pen speed within a stroke). On a
    connector ``a→b`` the position is ``a + (b−a)·s(u)`` with smoothstep
    ``s(u)=3u²−2u³`` (zero velocity at both ends); pen-down segments interpolate
    linearly. Returns ``(z_out (n,), label (n,))`` where each sample copies its
    segment's label, so connector samples are :data:`PEN_UP`.

    ``jump_time=0.0`` collapses connectors to zero time (a hard discontinuity).
    Raises :class:`ValueError` if the total pen-down length is zero.
    See docs/design.md §P6.
    """
    z = np.asarray(z, dtype=np.complex128)
    seg_label = np.asarray(seg_label, dtype=np.int16)
    m = z.shape[0]
    if m == 0:
        raise ValueError("cannot resample an empty tour")

    seg_vec = np.diff(np.concatenate([z, z[:1]]))  # (m,) segment i: z[i]->z[i+1]
    seg_len = np.abs(seg_vec)
    penup = seg_label == PEN_UP
    pendown = ~penup
    pendown_total = float(seg_len[pendown].sum())
    if pendown_total <= 0.0:
        raise ValueError("cannot resample a zero pen-down length tour")

    n_jumps = int(penup.sum())
    jump_total = float(jump_time) * n_jumps
    if jump_total >= 1.0:  # always leave room for the visible strokes
        jump_total = 1.0 - 1e-9
    seg_time = np.zeros(m, dtype=np.float64)
    if n_jumps:
        seg_time[penup] = jump_total / n_jumps
    seg_time[pendown] = (1.0 - jump_total) * seg_len[pendown] / pendown_total

    t_edges = np.concatenate([[0.0], np.cumsum(seg_time)])
    t_edges[-1] = 1.0
    ts = np.arange(n) / n
    seg_idx = np.clip(np.searchsorted(t_edges, ts, side="right") - 1, 0, m - 1)
    st = seg_time[seg_idx]
    u = np.where(st > 0.0, (ts - t_edges[seg_idx]) / np.where(st > 0.0, st, 1.0), 0.0)

    is_up = penup[seg_idx]
    frac = np.where(is_up, 3.0 * u**2 - 2.0 * u**3, u)  # smoothstep on connectors
    z_out = (z[seg_idx] + frac * seg_vec[seg_idx]).astype(np.complex128)
    return z_out, seg_label[seg_idx].astype(np.int16)
