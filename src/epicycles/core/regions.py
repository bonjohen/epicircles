"""Palette regions and interior-coloured boundaries (U21, FR-15). Pure.

See docs/design.md §core/regions.py for the contract.
"""
from __future__ import annotations

import numpy as np
from PIL import Image
from skimage.measure import find_contours

_PROBE = 0.75  # px to the left/right of a segment midpoint
_VOTES = 32


def quantize(rgb: np.ndarray, p: int) -> tuple[np.ndarray, np.ndarray]:
    """Median-cut palette of at most ``p`` colours, no dithering (deterministic)."""
    img = Image.fromarray(np.asarray(rgb, dtype=np.uint8), "RGB")
    q = img.quantize(colors=int(p), method=Image.Quantize.MEDIANCUT,
                     dither=Image.Dither.NONE)
    index = np.asarray(q, dtype=np.uint8)
    used = int(index.max()) + 1
    pal = np.asarray(q.getpalette()[: 3 * used], dtype=np.uint8).reshape(-1, 3)
    return index, pal


def background_index(index: np.ndarray) -> int:
    """Palette index with the most border pixels; ties → lowest index."""
    border = np.concatenate([index[0], index[-1], index[1:-1, 0], index[1:-1, -1]])
    counts = np.bincount(border.astype(np.int64))
    return int(np.argmax(counts))


def _to_xy(rc: np.ndarray, h: int) -> np.ndarray:
    """(row, col) in unpadded pixel-index coords → pixel-centre complex x+iy."""
    return (rc[:, 1] + 0.5) + 1j * (h - rc[:, 0] - 0.5)


def _pixel_at(index: np.ndarray, pt: complex) -> int:
    h, w = index.shape
    col = int(np.floor(pt.real))
    row = int(np.floor(h - pt.imag))
    if 0 <= row < h and 0 <= col < w:
        return int(index[row, col])
    return -1


def _side_probe(z: np.ndarray, i: int, side: float) -> complex:
    a, b = z[i], z[(i + 1) % len(z)]
    d = b - a
    normal = 1j * d / abs(d)  # left of travel direction in y-up coords
    return (a + b) / 2 + side * _PROBE * normal


def _orient_left(z: np.ndarray, index: np.ndarray, region: int) -> np.ndarray:
    seg = np.abs(np.roll(z, -1) - z)
    i = int(np.argmax(seg))
    if _pixel_at(index, _side_probe(z, i, +1.0)) != region:
        return z[::-1].copy()
    return z


def _neighbour(z: np.ndarray, index: np.ndarray) -> int:
    seg = np.abs(np.roll(z, -1) - z)
    good = np.flatnonzero(seg > 1e-9)
    picks = good[np.linspace(0, len(good) - 1, min(_VOTES, len(good))).astype(int)]
    votes = [_pixel_at(index, _side_probe(z, i, -1.0)) for i in picks]
    vals, counts = np.unique(np.asarray(votes), return_counts=True)
    return int(vals[np.argmax(counts)])


def region_boundaries(
    index: np.ndarray, mode: str = "both", min_len: int = 8
) -> list[tuple[np.ndarray, int]]:
    """Boundaries of every non-background palette region, region on the left."""
    if mode not in ("both", "foreground"):
        raise ValueError(f"mode must be 'both' or 'foreground', not {mode!r}")
    index = np.asarray(index)
    h, _ = index.shape
    bg = background_index(index)
    areas = np.bincount(index.ravel().astype(np.int64))
    out: list[tuple[np.ndarray, int, int, tuple]] = []
    for region in range(len(areas)):
        if region == bg or areas[region] == 0:
            continue
        mask = np.pad(index == region, 1).astype(float)
        for rc in find_contours(mask, 0.5):
            rc = rc[:-1] - 1.0 if np.allclose(rc[0], rc[-1]) else rc - 1.0
            if len(rc) < min_len:
                continue
            z = _orient_left(_to_xy(rc, h), index, region)
            if mode == "foreground":
                nb = _neighbour(z, index)
                if nb >= 0 and nb != bg and areas[nb] < areas[region]:
                    continue
            out.append((z, region, -len(z), (rc[0, 0], rc[0, 1])))
    out.sort(key=lambda t: (t[1], t[2], t[3]))
    return [(z, region) for z, region, _, _ in out]
