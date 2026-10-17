"""Load a raster image as a grayscale array, downscaled to a max dimension."""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image


def _has_alpha(img: Image.Image) -> bool:
    return img.mode in ("RGBA", "LA", "PA") or (
        img.mode == "P" and "transparency" in img.info
    )


def load_gray(path: str | Path, max_dim: int) -> np.ndarray:
    """Return a ``uint8`` grayscale array with ``max(H, W) <= max_dim``.

    Alpha images are composited over white before the "L" conversion; a white
    glyph on a transparent field (which would flatten to uniform white) instead
    uses ``255 - alpha`` as ink. See docs/design.md#ioimagepy.
    """
    img = Image.open(path)
    if _has_alpha(img):
        rgba = img.convert("RGBA")
        alpha = np.array(rgba.getchannel("A"), dtype=np.uint8)
        white = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
        gray = Image.alpha_composite(white, rgba).convert("L")
        arr = np.array(gray, dtype=np.uint8)
        if arr.min() == arr.max() and alpha.min() != alpha.max():
            gray = Image.fromarray((255 - alpha).astype(np.uint8), "L")
    else:
        gray = img.convert("L")

    w, h = gray.size
    longest = max(w, h)
    if longest > max_dim:
        scale = max_dim / longest
        gray = gray.resize(
            (max(1, round(w * scale)), max(1, round(h * scale))), Image.LANCZOS
        )
    return np.array(gray, dtype=np.uint8)


def load_rgb(path: str | Path, max_dim: int) -> np.ndarray:
    """Return a ``uint8`` HxWx3 array, alpha composited over white, ``max(H,W) <= max_dim``."""
    img = Image.open(path)
    if _has_alpha(img):
        rgba = img.convert("RGBA")
        white = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
        rgb = Image.alpha_composite(white, rgba).convert("RGB")
    else:
        rgb = img.convert("RGB")
    w, h = rgb.size
    longest = max(w, h)
    if longest > max_dim:
        scale = max_dim / longest
        rgb = rgb.resize((max(1, round(w * scale)), max(1, round(h * scale))), Image.LANCZOS)
    return np.array(rgb, dtype=np.uint8)
