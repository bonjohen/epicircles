"""Load an SVG into strokes, with transforms applied and y pointing up.

Uses ``svgpathtools.Document(path).paths()`` so group and element ``transform``
attributes are baked into the returned geometry (``svg2paths`` ignores them).
Basic shapes (``circle``, ``rect``, ``line``, ``polyline``) are converted to
paths by svgpathtools. Each continuous subpath becomes one open stroke.

Sampling is scale-invariant: the total point budget ``samples`` is divided among
subpaths in proportion to arc length, ``n_i = max(8, round(samples·len_i/Σlen))``.
An absolute per-unit density would collapse small-viewBox icons (e.g. a
``0 0 24 24`` viewBox) to 8-point polygons and lose the curves before the DFT.
SVG's y axis points down; we negate it (``y_up = -y_svg``, complex conjugation)
so higher on screen means larger y.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from svgpathtools import Document


def load_svg(path: str | Path, samples: int) -> list[np.ndarray]:
    """Return one stroke per continuous subpath, sharing a point budget by length."""
    doc = Document(str(path))
    subpaths = [
        sub for full_path in doc.paths() for sub in full_path.continuous_subpaths()
    ]
    lengths = [sub.length() for sub in subpaths]
    total = sum(lengths) or 1.0

    strokes: list[np.ndarray] = []
    for sub, length in zip(subpaths, lengths):
        n = max(8, round(samples * length / total))
        ts = np.linspace(0.0, 1.0, n)
        pts = np.array([sub.point(t) for t in ts], dtype=np.complex128)
        strokes.append(np.conjugate(pts))  # y_up = -y_svg
    return strokes
