"""Join open strokes into a single closed tour.

Greedy nearest-endpoint ordering: start with stroke 0, then repeatedly append
the unused stroke whose nearer endpoint is closest to the current end (reversing
that stroke if its far endpoint is the closer one). Ties break to the lowest
index, then to forward orientation. The connector length is the sum of the join
gaps plus the closing jump from the tour's last point back to its first — except
a stroke that is already closed (last point == first within ``1e-9*scale``) has
its duplicate endpoint dropped and contributes no closing length.
"""
from __future__ import annotations

import numpy as np

#: Segment label for connector/closing jumps; renderers must not draw these.
PEN_UP = -1


def _scale(points: np.ndarray) -> float:
    if points.size == 0:
        return 1.0
    s = max(float(np.ptp(points.real)), float(np.ptp(points.imag)))
    return s if s > 0 else 1.0


def join_labeled(
    strokes: list[np.ndarray], labels: list[int] | None = None
) -> tuple[np.ndarray, np.ndarray, float]:
    """Return ``(tour, seg_label, connector_len)`` for a list of strokes.

    ``tour`` is the bare ``complex128 (n,)`` path (identical to
    :func:`join_strokes`). ``seg_label`` is ``int16 (n,)`` labelling each segment
    ``tour[i] → tour[(i+1) % n]``: a pen-down segment inside a stroke carries that
    stroke's colour (``labels[j]``, default 0); the connector segments between
    strokes and the closing jump carry :data:`PEN_UP`. A lone **closed** stroke
    has no pen-up segment (its closure is drawn). See docs/design.md §P6.
    """
    strokes = [np.asarray(s, dtype=np.complex128) for s in strokes]
    if not strokes:
        return (
            np.array([], dtype=np.complex128),
            np.array([], dtype=np.int16),
            0.0,
        )
    if labels is None:
        labels = [0] * len(strokes)

    tol = 1e-9 * _scale(np.concatenate(strokes))
    closed = [len(s) >= 3 and abs(s[-1] - s[0]) <= tol for s in strokes]
    n = len(strokes)

    used = [False] * n
    used[0] = True
    order: list[tuple[int, bool]] = [(0, False)]
    cur_end = strokes[0][-1]
    joins = 0.0

    for _ in range(n - 1):
        best: tuple[float, int, int] | None = None
        for j in range(n):
            if used[j]:
                continue
            s = strokes[j]
            for dist, orient in ((abs(cur_end - s[0]), 0), (abs(cur_end - s[-1]), 1)):
                key = (dist, j, orient)
                if best is None or key < best:
                    best = key
        dist, j, orient = best  # type: ignore[misc]
        used[j] = True
        order.append((j, bool(orient)))
        joins += dist
        s = strokes[j]
        cur_end = s[0] if orient == 1 else s[-1]

    segments: list[np.ndarray] = []
    seg_labels: list[np.ndarray] = []
    first_start = None
    last_end = None
    for idx, (j, rev) in enumerate(order):
        s = strokes[j][::-1] if rev else strokes[j]
        if idx == 0:
            first_start = s[0]
        last_end = s[-1]  # pre-drop endpoint, used for the closing jump
        pts = s[:-1] if closed[j] else s
        segments.append(pts)
        colour = int(labels[j])
        # pen-down segments within this stroke
        seg_labels.append(np.full(len(pts) - 1, colour, dtype=np.int16))
        # the segment leaving this stroke's last point
        if idx < n - 1:
            seg_labels.append(np.array([PEN_UP], dtype=np.int16))  # connector
        elif n == 1 and closed[j]:
            seg_labels.append(np.array([colour], dtype=np.int16))  # natural closure
        else:
            seg_labels.append(np.array([PEN_UP], dtype=np.int16))  # closing jump

    tour = np.concatenate(segments)
    seg_label = np.concatenate(seg_labels)
    closing = abs(last_end - first_start)
    if closing <= tol:
        closing = 0.0
    return tour, seg_label, float(joins + closing)


def join_strokes(strokes: list[np.ndarray]) -> tuple[np.ndarray, float]:
    """Return ``(tour, connector_len)`` for a list of open strokes (v1).

    Thin wrapper over :func:`join_labeled` that drops the labels, preserving the
    original bare-tour signature for existing callers.
    """
    tour, _seg_label, connector_len = join_labeled(strokes)
    return tour, connector_len


def _endpoints(stroke: np.ndarray, reverse: bool) -> tuple[complex, complex]:
    """(start, end) of a stroke in the given orientation."""
    if reverse:
        return complex(stroke[-1]), complex(stroke[0])
    return complex(stroke[0]), complex(stroke[-1])


def order_connector_length(
    strokes: list[np.ndarray], order: list[tuple[int, bool]]
) -> float:
    """Cyclic connector length of an ``(index, reversed)`` ordering.

    ``Σ_i |end(order[i]) − start(order[i+1])|`` including the closing jump from
    the last stroke's end back to the first stroke's start.
    """
    pts = [_endpoints(strokes[i], rev) for i, rev in order]
    n = len(pts)
    return float(
        sum(abs(pts[k][1] - pts[(k + 1) % n][0]) for k in range(n))
    )


def two_opt(
    strokes: list[np.ndarray], order: list[tuple[int, bool]]
) -> list[tuple[int, bool]]:
    """Improve a stroke ordering with strictly-improving cyclic 2-opt moves.

    A move reverses a contiguous sub-segment ``order[i:j+1]`` (flipping each
    stroke's orientation). Only moves that strictly reduce
    :func:`order_connector_length` are accepted, so the connector length never
    increases; the fixed scan order makes the result deterministic.
    """
    order = list(order)
    n = len(order)
    best = order_connector_length(strokes, order)
    improved = True
    while improved:
        improved = False
        for i in range(n):
            for j in range(i + 1, n):
                cand = (
                    order[:i]
                    + [(idx, not rev) for idx, rev in reversed(order[i : j + 1])]
                    + order[j + 1 :]
                )
                length = order_connector_length(strokes, cand)
                if length < best - 1e-12:
                    order, best, improved = cand, length, True
    return order
