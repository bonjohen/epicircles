"""U21 / FR-15 / AC-6: palette regions, interior-coloured boundaries."""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw

from epicycles.core.regions import background_index, quantize, region_boundaries

WHITE, BROWN, BLUE = (255, 255, 255), (140, 80, 30), (30, 60, 220)


def _scene(ring=False):
    im = Image.new("RGB", (120, 120), WHITE)
    d = ImageDraw.Draw(im)
    d.rectangle([20, 20, 99, 99], fill=BROWN)
    d.ellipse([40, 40, 79, 79], fill=WHITE if ring else BLUE)
    return np.asarray(im)


def _signed_area(z):
    x, y = z.real, z.imag
    return 0.5 * float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))


def _colour(palette, idx):
    return tuple(int(v) for v in palette[idx])


def test_quantize_is_deterministic():
    rgb = _scene()
    a = quantize(rgb, 6)
    b = quantize(rgb, 6)
    assert np.array_equal(a[0], b[0]) and np.array_equal(a[1], b[1])
    assert a[0].shape == rgb.shape[:2]


def test_background_is_the_border_colour():
    index, palette = quantize(_scene(), 6)
    assert _colour(palette, background_index(index)) == WHITE


def test_ac6_foreground_two_loops_disk_blue_square_brown():
    index, palette = quantize(_scene(), 6)
    out = region_boundaries(index, mode="foreground")
    cols = sorted(_colour(palette, c) for _, c in out)
    assert cols == sorted([BLUE, BROWN])
    for z, c in out:  # region on the left => outer loops are counter-clockwise
        assert _signed_area(z) > 0


def test_ac6_both_three_loops_shared_edge_twice():
    index, palette = quantize(_scene(), 6)
    out = region_boundaries(index)  # default "both"
    cols = sorted(_colour(palette, c) for _, c in out)
    assert cols == sorted([BLUE, BROWN, BROWN])


def test_hole_is_reversed_and_keeps_ring_colour():
    index, palette = quantize(_scene(ring=True), 6)
    out = region_boundaries(index)
    assert len(out) == 2 and all(_colour(palette, c) == BROWN for _, c in out)
    areas = sorted(_signed_area(z) for z, _ in out)
    assert areas[0] < 0 < areas[1]  # hole clockwise, outer counter-clockwise


def test_ac6_no_pendown_sample_near_connector():
    from epicycles.core.path import resample_labeled
    from epicycles.core.tour import PEN_UP, join_labeled

    index, _ = quantize(_scene(), 6)
    out = region_boundaries(index, mode="foreground")
    strokes = [z for z, _ in out]
    z, seg, _ = join_labeled(strokes, labels=[c for _, c in out])
    zr, lab = resample_labeled(z, seg, 2048, jump_time=0.01)
    pts = np.concatenate(strokes)
    pen = zr[np.asarray(lab) != PEN_UP]
    d = np.min(np.abs(pen[:, None] - pts[None, :]), axis=1)
    assert float(d.max()) < 1.0


def test_cli_regions_kind(tmp_path):
    from epicycles.cli import main

    p = tmp_path / "scene.png"
    Image.fromarray(_scene()).save(p)
    js = tmp_path / "c.json"
    rc = main(["draw", str(p), "--kind", "regions", "--palette", "4",
               "--boundaries", "foreground", "--terms", "64", "--frames", "4",
               "--json", str(js), "--out", str(tmp_path / "o.gif")])
    assert rc == 0 and js.exists() and (tmp_path / "o.gif").exists()
