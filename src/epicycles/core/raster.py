"""Raster image operations: binarize and skeletonize.

Ink is the dark strokes on a light background. ``binarize`` returns a boolean
ink mask (Otsu threshold by default); ``skeleton`` thins it to a 1-pixel-wide
centreline. Edge detection and pruning are added in later units.
"""
from __future__ import annotations

import numpy as np
from scipy.ndimage import convolve
from skimage.feature import canny
from skimage.filters import threshold_otsu
from skimage.measure import label
from skimage.morphology import skeletonize
from skimage.util import img_as_float

_DEG_KERNEL = np.array([[1, 1, 1], [1, 0, 1], [1, 1, 1]])


def binarize(gray: np.ndarray, threshold: int | None = None) -> np.ndarray:
    """Boolean ink mask: ``True`` where darker than ``threshold`` (Otsu if None)."""
    gray = np.asarray(gray)
    if threshold is None:
        threshold = threshold_otsu(gray)
    return gray <= threshold


def skeleton(mask: np.ndarray) -> np.ndarray:
    """1-pixel-wide skeleton of the ink mask (``skimage.skeletonize``)."""
    return skeletonize(np.asarray(mask, dtype=bool))


def edges(gray: np.ndarray, sigma: float, low: float, high: float) -> np.ndarray:
    """Canny edge mask. Thresholds are absolute gradients on the [0,1] scale.

    The image is converted to float in ``[0, 1]`` (``skimage.util.img_as_float``)
    so ``low``/``high`` are comparable across uint8/float inputs.
    """
    f = img_as_float(np.asarray(gray))
    return canny(f, sigma=sigma, low_threshold=low, high_threshold=high)


def _degree(skel: np.ndarray) -> np.ndarray:
    """8-neighbour count for each pixel (0 off-skeleton pixels included)."""
    return convolve(skel.astype(int), _DEG_KERNEL, mode="constant", cval=0)


_RING = ((-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1))


def _neighbours8(r: int, c: int, skel: np.ndarray):
    h, w = skel.shape
    for dr, dc in _RING:
        nr, nc = r + dr, c + dc
        if 0 <= nr < h and 0 <= nc < w and skel[nr, nc]:
            yield nr, nc


def _neighbour_groups(r: int, c: int, skel: np.ndarray) -> int:
    """Number of 8-connected groups of set pixels around (r, c) on the 3x3 ring.

    Endpoint -> 1, mid-path -> 2, junction -> >=3. Using groups (not raw degree)
    avoids counting a pass-through pixel that merely touches the main line
    diagonally as a junction.
    """
    h, w = skel.shape
    ring = [
        0 <= r + dr < h and 0 <= c + dc < w and skel[r + dr, c + dc]
        for dr, dc in _RING
    ]
    if all(ring):
        return 1
    return sum(1 for i in range(8) if ring[i] and not ring[i - 1])


def skeleton_to_strokes_euler(skel: np.ndarray) -> list[np.ndarray]:
    """Like :func:`skeleton_to_strokes` but avoids retracing where possible.

    For each 8-connected component whose pixel graph is Eulerian (every vertex
    has even degree — e.g. a closed loop), a Hierholzer Euler circuit traverses
    each edge exactly once (no out-and-back doubling). Components with
    odd-degree vertices (trees, T-junctions) fall back to the DFS walk. The
    total walk length is therefore never longer than the pure DFS walk.
    """
    skel = np.asarray(skel, dtype=bool)
    h = skel.shape[0]
    labels = label(skel, connectivity=2)

    def to_complex(rc: tuple[int, int]) -> complex:
        r, c = rc
        return complex(c + 0.5, h - r - 0.5)

    components = []
    for lab in range(1, int(labels.max()) + 1):
        nodes = sorted(zip(*np.where(labels == lab)))
        if nodes:
            components.append((nodes[0], lab, nodes))
    components.sort(key=lambda t: t[0])  # deterministic: by lowest (row,col)

    strokes: list[np.ndarray] = []
    for _, lab, nodes in components:
        node_set = set(nodes)
        if len(nodes) < 2:
            continue
        # Build undirected edges (each adjacent pair once) with ids.
        adj: dict[tuple[int, int], list[tuple[tuple[int, int], int]]] = {
            n: [] for n in nodes
        }
        edge_id = 0
        for r, c in nodes:
            for dr, dc in _RING:
                nb = (r + dr, c + dc)
                if nb in node_set and (r, c) < nb:
                    adj[(r, c)].append((nb, edge_id))
                    adj[nb].append(((r, c), edge_id))
                    edge_id += 1
        for n in adj:
            adj[n].sort()  # deterministic traversal order

        if edge_id > 0 and all(len(adj[n]) % 2 == 0 for n in nodes):
            circuit = _hierholzer(nodes[0], adj, edge_id)
            # circuit returns to the start; drop the repeated final point.
            if len(circuit) >= 2 and circuit[-1] == circuit[0]:
                circuit = circuit[:-1]
            if len(circuit) >= 2:
                strokes.append(
                    np.array([to_complex(p) for p in circuit], dtype=np.complex128)
                )
        else:
            strokes.extend(skeleton_to_strokes(labels == lab))
    return strokes


def _hierholzer(
    start: tuple[int, int],
    adj: dict[tuple[int, int], list[tuple[tuple[int, int], int]]],
    n_edges: int,
) -> list[tuple[int, int]]:
    """Euler circuit of an Eulerian undirected multigraph (iterative)."""
    cursor = {n: 0 for n in adj}  # next adjacency index to consider per node
    used = [False] * n_edges
    stack = [start]
    circuit: list[tuple[int, int]] = []
    while stack:
        v = stack[-1]
        advanced = False
        while cursor[v] < len(adj[v]):
            nb, eid = adj[v][cursor[v]]
            cursor[v] += 1
            if not used[eid]:
                used[eid] = True
                stack.append(nb)
                advanced = True
                break
        if not advanced:
            circuit.append(stack.pop())
    circuit.reverse()
    return circuit


def prune(skel: np.ndarray, min_component_px: int, spur_len: int) -> np.ndarray:
    """Drop small 8-connected components and remove short dead-end branches."""
    skel = np.asarray(skel, dtype=bool).copy()

    # 1. Remove components smaller than min_component_px.
    labels = label(skel, connectivity=2)
    if labels.max() > 0:
        counts = np.bincount(labels.ravel())
        for lab in range(1, labels.max() + 1):
            if counts[lab] < min_component_px:
                skel[labels == lab] = False

    # 2. Iteratively remove dead-end branches shorter than spur_len. A branch
    #    runs from a free endpoint (1 neighbour group) to a junction (>=3
    #    groups); it is a spur if it reaches a junction in fewer than spur_len
    #    pixels.
    changed = True
    while changed:
        changed = False
        pixels = list(zip(*np.where(skel)))
        groups = {p: _neighbour_groups(*p, skel) for p in pixels}
        junction = {p for p, g in groups.items() if g >= 3}
        endpoints = [p for p, g in groups.items() if g == 1]
        for ep in endpoints:
            branch: list[tuple[int, int]] = []
            seen = {ep}
            frontier = [ep]
            reached_junction = False
            while frontier and len(branch) < spur_len:
                cur = frontier.pop()
                branch.append(cur)
                if any(nb in junction for nb in _neighbours8(*cur, skel)):
                    # cur abuts the junction: stop here, do not leak past it
                    # (its other neighbours belong to the trunk, reachable only
                    # via 8-diagonals around the junction).
                    reached_junction = True
                    continue
                for nb in _neighbours8(*cur, skel):
                    if nb not in seen and nb not in junction:
                        seen.add(nb)
                        frontier.append(nb)
            if reached_junction and len(branch) < spur_len:
                for p in branch:
                    skel[p] = False
                changed = True

    return skel


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
