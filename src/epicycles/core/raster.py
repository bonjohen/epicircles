"""Raster image operations: binarize and skeletonize.

Ink is the dark strokes on a light background. ``binarize`` returns a boolean
ink mask (Otsu threshold by default); ``skeleton`` thins it to a 1-pixel-wide
centreline. Edge detection and pruning are added in later units.
"""
from __future__ import annotations

import numpy as np
from skimage.filters import threshold_otsu
from skimage.morphology import skeletonize


def binarize(gray: np.ndarray, threshold: int | None = None) -> np.ndarray:
    """Boolean ink mask: ``True`` where darker than ``threshold`` (Otsu if None)."""
    gray = np.asarray(gray)
    if threshold is None:
        threshold = threshold_otsu(gray)
    return gray <= threshold


def skeleton(mask: np.ndarray) -> np.ndarray:
    """1-pixel-wide skeleton of the ink mask (``skimage.skeletonize``)."""
    return skeletonize(np.asarray(mask, dtype=bool))


# Neighbour offsets in fixed order N, NE, E, SE, S, SW, W, NW (row, col deltas).
_NEIGHBORS = ((-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1))


def skeleton_to_strokes(skel: np.ndarray) -> list[np.ndarray]:
    """One stroke per 8-connected component via an iterative DFS closed walk.

    Each component's DFS spanning tree is traversed out-and-back (every tree
    edge twice), which always yields a valid closed walk — at the cost of
    drawing each edge twice (loops are retraced). A tree of ``p`` pixels yields
    ``2(p-1)`` points; the final return to the start is not repeated. The walk
    starts at the component's lowest ``(row, col)`` pixel and explores
    neighbours in the fixed order N, NE, E, SE, S, SW, W, NW. Pixel centres map
    to ``x = col + 0.5``, ``y = H - row - 0.5`` (y up). Implemented with an
    explicit stack — real skeletons exceed Python's recursion limit.
    """
    skel = np.asarray(skel, dtype=bool)
    h = skel.shape[0]
    present = {(int(r), int(c)) for r, c in zip(*np.where(skel))}

    def to_complex(rc: tuple[int, int]) -> complex:
        r, c = rc
        return complex(c + 0.5, h - r - 0.5)

    def neighbours(rc: tuple[int, int]):
        r, c = rc
        for dr, dc in _NEIGHBORS:
            nb = (r + dr, c + dc)
            if nb in present:
                yield nb

    visited: set[tuple[int, int]] = set()
    strokes: list[np.ndarray] = []

    for start in sorted(present):  # sorted -> first unvisited is component min
        if start in visited:
            continue
        visited.add(start)
        walk = [start]
        stack = [(start, neighbours(start))]
        while stack:
            node, it = stack[-1]
            advanced = False
            for nb in it:
                if nb not in visited:
                    visited.add(nb)
                    walk.append(nb)
                    stack.append((nb, neighbours(nb)))
                    advanced = True
                    break
            if not advanced:
                stack.pop()
                if stack:
                    walk.append(stack[-1][0])  # backtrack step
        # walk ends by returning to start; drop that repeated final point.
        if len(walk) >= 2 and walk[-1] == start:
            walk.pop()
        if len(walk) >= 2:
            strokes.append(np.array([to_complex(p) for p in walk], dtype=np.complex128))
    return strokes
