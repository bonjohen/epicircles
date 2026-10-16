"""U14: Canny edges on the [0,1] float scale.

Contract in docs/design.md#core/raster.py: edges(gray, sigma, low, high) ->
bool HxW via img_as_float then skimage.feature.canny; thresholds are absolute
gradient values on the [0,1] scale.
"""
import numpy as np
from PIL import Image, ImageDraw

from epicycles.core.raster import edges


def test_disk_gives_edge_ring_within_1_5px():
    img = Image.new("L", (100, 100), 0)
    ImageDraw.Draw(img).ellipse([20, 20, 80, 80], fill=255)  # radius 30, centre (50,50)
    e = edges(np.array(img, np.uint8), sigma=2.0, low=0.1, high=0.2)
    assert e.sum() > 0
    ys, xs = np.where(e)
    r = np.hypot(xs - 50, ys - 50)
    assert np.all(np.abs(r - 30) <= 1.5)  # proves the [0,1] conversion + thresholds


def test_higher_sigma_gives_fewer_edges():
    rng = np.random.default_rng(0)
    noise = (rng.random((80, 80)) * 255).astype(np.uint8)
    fewer = edges(noise, sigma=3.0, low=0.1, high=0.2).sum()
    more = edges(noise, sigma=1.0, low=0.1, high=0.2).sum()
    assert fewer < more
