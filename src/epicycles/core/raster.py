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
