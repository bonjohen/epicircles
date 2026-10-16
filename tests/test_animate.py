"""U9: animation writer (I/O). Asserts on frame count, never on pixels."""
import numpy as np
from PIL import Image

from epicycles.core.fourier import select, spectrum
from epicycles.render.animate import write_animation


def _spec(n=16, m=4):
    j = np.arange(n)
    z = (1 - 1j) + 2.0 * np.exp(2j * np.pi * j / n) + 0.5 * np.exp(-2j * np.pi * j / n)
    return select(spectrum(z), m, "magnitude")


def test_write_gif_has_expected_frame_count(tmp_path):
    out = tmp_path / "anim.gif"
    write_animation(_spec(), out, n_frames=8, fps=10)
    assert out.exists() and out.stat().st_size > 0
    with Image.open(out) as im:
        assert getattr(im, "n_frames", 1) == 8
