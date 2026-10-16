"""U11: binarize (Otsu) and skeleton.

Contract in docs/design.md#core/raster.py:
  binarize(gray, threshold) -> bool HxW, True=ink, darker than threshold;
    None -> Otsu.
  skeleton(mask) -> bool HxW via skimage.morphology.skeletonize.
"""
import numpy as np
from PIL import Image, ImageDraw

from epicycles.core.raster import binarize, skeleton


def _rectangle_outline():
    img = Image.new("L", (60, 60), 255)
    ImageDraw.Draw(img).rectangle([15, 15, 45, 45], outline=0, width=3)
    return np.array(img, dtype=np.uint8)


def _no_full_2x2(sk: np.ndarray) -> bool:
    s = sk.astype(int)
    block = s[:-1, :-1] + s[1:, :-1] + s[:-1, 1:] + s[1:, 1:]
    return bool((block < 4).all())


def test_otsu_picks_ink_on_white_background():
    gray = _rectangle_outline()
    mask = binarize(gray, None)
    assert 0 < mask.sum() < gray.size
    assert mask[30, 15]  # left edge (row=y, col=x) is ink
    assert not mask[30, 30]  # interior is background


def test_explicit_threshold_marks_darker_as_ink():
    gray = np.array([[0, 100, 200, 255]], dtype=np.uint8)
    mask = binarize(gray, 150)
    assert list(mask[0]) == [True, True, False, False]


def test_skeleton_is_one_px_wide_near_centreline():
    mask = binarize(_rectangle_outline(), None)
    skel = skeleton(mask)
    assert skel.sum() < mask.sum()  # thinned
    assert _no_full_2x2(skel)  # 1 px wide
    ys, xs = np.where(skel)
    on_edge = (
        (np.abs(xs - 15) <= 1)
        | (np.abs(xs - 45) <= 1)
        | (np.abs(ys - 15) <= 1)
        | (np.abs(ys - 45) <= 1)
    )
    assert on_edge.mean() > 0.95  # within 1 px of the rectangle centreline
