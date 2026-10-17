"""F7.2: load_gray alpha handling + a clear 'no ink' error.

A white-on-transparent glyph must not flatten to uniform white (which would
misdetect as a blank photo and fail deep in resample). All-white input must
raise a clear error. Tests build their own images; no network, no pixel asserts.
"""
import numpy as np
import pytest
from PIL import Image, ImageDraw

from epicycles.cli import run_lineart_pipeline
from epicycles.io.image import load_gray


def _white_ring_on_transparent(size=160):
    """RGBA: opaque white ring outline on a transparent-white field.

    The background RGB is white, so a plain alpha-dropping ``convert("L")``
    flattens the whole image to uniform white (the F7.2 bug). Correct handling
    must recover the ring as ink.
    """
    img = Image.new("RGBA", (size, size), (255, 255, 255, 0))
    ImageDraw.Draw(img).ellipse(
        [30, 30, size - 30, size - 30], outline=(255, 255, 255, 255), width=3
    )
    return img


def test_load_gray_alpha_becomes_ink(tmp_path):
    p = tmp_path / "ring.png"
    _white_ring_on_transparent().save(p)
    gray = load_gray(str(p), 160)
    # The glyph must survive as ink: the image is not uniform, and the ring
    # pixels are darker (ink) than the transparent background.
    assert gray.min() != gray.max()
    assert int(gray.min()) < 128 < int(gray.max())


def test_run_lineart_on_white_on_transparent_reconstructs(tmp_path):
    p = tmp_path / "ring.png"
    _white_ring_on_transparent().save(p)
    res = run_lineart_pipeline(str(p), "auto", 64, "magnitude")
    assert res.n_strokes >= 1
    assert len(res.z) == res.n


@pytest.mark.parametrize("pipeline", ["lineart", "photo"])
def test_all_white_image_raises_clear_no_ink_error(tmp_path, pipeline):
    from epicycles.cli import run_photo_pipeline

    run = {"lineart": run_lineart_pipeline, "photo": run_photo_pipeline}[pipeline]
    p = tmp_path / "blank.png"
    Image.new("L", (120, 120), 255).save(p)
    with pytest.raises(ValueError, match="no ink found in image"):
        run(str(p), "auto", 64, "magnitude")
