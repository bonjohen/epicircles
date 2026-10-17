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


Colour = tuple[int, int, int]
INK: Colour = (0, 0, 0)

_NAMED: dict[str, Colour] = {
    "black": (0, 0, 0), "white": (255, 255, 255), "red": (255, 0, 0),
    "green": (0, 128, 0), "lime": (0, 255, 0), "blue": (0, 0, 255),
    "yellow": (255, 255, 0), "cyan": (0, 255, 255), "aqua": (0, 255, 255),
    "magenta": (255, 0, 255), "fuchsia": (255, 0, 255), "gray": (128, 128, 128),
    "grey": (128, 128, 128), "silver": (192, 192, 192), "maroon": (128, 0, 0),
    "olive": (128, 128, 0), "navy": (0, 0, 128), "purple": (128, 0, 128),
    "teal": (0, 128, 128), "orange": (255, 165, 0), "brown": (165, 42, 42),
    "pink": (255, 192, 203),
}


def _parse_colour(value: str) -> Colour | None:
    """Parse an SVG colour value; None if unparseable or not a solid colour."""
    v = value.strip().lower()
    if v.startswith("#") and len(v) in (4, 7):
        h = v[1:]
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        try:
            return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
        except ValueError:
            return None
    if v.startswith("rgb(") and v.endswith(")"):
        try:
            r, g, b = (int(float(x)) for x in v[4:-1].split(","))
        except ValueError:
            return None
        return (max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)))
    return _NAMED.get(v)


def _declared_stroke(elem) -> str | None:
    """The element's own stroke: style declaration wins over the attribute."""
    for decl in (elem.get("style") or "").split(";"):
        if ":" in decl:
            key, val = decl.split(":", 1)
            if key.strip() == "stroke":
                return val.strip()
    return elem.get("stroke")


def _resolve_colour(elem, parent: dict) -> Colour:
    """Nearest stroke declaration up the ancestor chain; else default ink."""
    node = elem
    while node is not None:
        value = _declared_stroke(node)
        if value is not None:
            parsed = _parse_colour(value)
            return parsed if parsed is not None else INK
        node = parent.get(node)
    return INK


def load_svg_coloured(
    path: str | Path, samples: int
) -> tuple[list[np.ndarray], list[Colour]]:
    """Strokes as in :func:`load_svg`, plus one ``(r,g,b)`` colour per stroke."""
    doc = Document(str(path))
    parent = {child: p for p in doc.tree.iter() for child in p}
    subpaths = []
    colours: list[Colour] = []
    for full_path in doc.paths():
        colour = _resolve_colour(getattr(full_path, "element", None), parent) \
            if getattr(full_path, "element", None) is not None else INK
        for sub in full_path.continuous_subpaths():
            subpaths.append(sub)
            colours.append(colour)
    lengths = [sub.length() for sub in subpaths]
    total = sum(lengths) or 1.0

    strokes: list[np.ndarray] = []
    for sub, length in zip(subpaths, lengths):
        n = max(8, round(samples * length / total))
        ts = np.linspace(0.0, 1.0, n)
        pts = np.array([sub.point(t) for t in ts], dtype=np.complex128)
        strokes.append(np.conjugate(pts))  # y_up = -y_svg
    return strokes, colours


def load_svg(path: str | Path, samples: int) -> list[np.ndarray]:
    """Return one stroke per continuous subpath, sharing a point budget by length."""
    return load_svg_coloured(path, samples)[0]
