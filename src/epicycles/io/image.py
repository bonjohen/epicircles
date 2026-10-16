"""Load a raster image as a grayscale array, downscaled to a max dimension."""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image


def load_gray(path: str | Path, max_dim: int) -> np.ndarray:
    """Return a ``uint8`` grayscale array with ``max(H, W) <= max_dim``."""
    img = Image.open(path).convert("L")
    w, h = img.size
    longest = max(w, h)
    if longest > max_dim:
        scale = max_dim / longest
        img = img.resize(
            (max(1, round(w * scale)), max(1, round(h * scale))), Image.LANCZOS
        )
    return np.array(img, dtype=np.uint8)
