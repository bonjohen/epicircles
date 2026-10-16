"""Load an SVG into strokes, with transforms applied and y pointing up.

Uses ``svgpathtools.Document(path).paths()`` so group and element ``transform``
attributes are baked into the returned geometry (``svg2paths`` ignores them).
Basic shapes (``circle``, ``rect``, ``line``, ``polyline``) are converted to
paths by svgpathtools. Each continuous subpath becomes one open stroke sampled
at ``max(8, ceil(length * samples_per_unit))`` points. SVG's y axis points
down; we negate it (``y_up = -y_svg``, i.e. complex conjugation) so higher on
screen means larger y.
"""
from __future__ import annotations

from math import ceil
from pathlib import Path

import numpy as np
from svgpathtools import Document


def load_svg(path: str | Path, samples_per_unit: float) -> list[np.ndarray]:
    """Return one stroke per continuous subpath of the SVG at ``path``."""
    doc = Document(str(path))
    strokes: list[np.ndarray] = []
    for full_path in doc.paths():
        for sub in full_path.continuous_subpaths():
            n = max(8, ceil(sub.length() * samples_per_unit))
            ts = np.linspace(0.0, 1.0, n)
            pts = np.array([sub.point(t) for t in ts], dtype=np.complex128)
            strokes.append(np.conjugate(pts))  # y_up = -y_svg
    return strokes
