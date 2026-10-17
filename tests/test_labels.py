"""U20 — labels, pen-up, smooth jumps. Contract: docs/design.md §P6.

Additive labelled API: ``join_labeled`` / ``resample_labeled`` /
``error(..., mask=)`` / ``to_json(..., segments=, background=)``. The v1
``join_strokes`` / ``resample`` stay bare-tour and unchanged.
"""
import json

import numpy as np

from epicycles.core.fourier import error, select, spectrum
from epicycles.core.path import resample, resample_labeled
from epicycles.core.tour import PEN_UP, join_labeled
from epicycles.io.export import to_json


def _two_strokes():
    """Two separate arcs → 2 strokes, so the tour has 2 pen-up connectors."""
    a = 5.0 + 5.0 * np.exp(1j * np.linspace(0.0, np.pi, 40))
    b = 5.0 + 20.0j + 5.0 * np.exp(1j * np.linspace(np.pi, 2 * np.pi, 40))
    return [a.astype(np.complex128), b.astype(np.complex128)]


def _on_some_stroke(p, strokes, tol=1e-6):
    for s in strokes:
        for i in range(len(s) - 1):
            a, b = s[i], s[i + 1]
            t = np.clip(np.real((p - a) * np.conj(b - a)) / abs(b - a) ** 2, 0.0, 1.0)
            if abs(p - (a + t * (b - a))) < tol:
                return True
    return False


def test_pen_up_constant():
    assert PEN_UP == -1


def test_join_labeled_marks_connectors_pen_up():
    z, seg, clen = join_labeled(_two_strokes())
    seg = np.asarray(seg)
    assert z.shape[0] == seg.shape[0]
    # the A→B join and the closing B→A jump are the two pen-up segments
    assert int((seg == PEN_UP).sum()) == 2
    assert set(np.unique(seg)).issubset({PEN_UP, 0})


def test_join_labeled_respects_colour_labels():
    z, seg, clen = join_labeled(_two_strokes(), labels=[2, 5])
    seg = np.asarray(seg)
    pen = seg[seg != PEN_UP]
    assert set(int(x) for x in np.unique(pen)) == {2, 5}


def test_labels_survive_join_resample():
    z, seg, clen = join_labeled(_two_strokes())
    zr, lab = resample_labeled(z, seg, 200, jump_time=0.05)
    lab = np.asarray(lab)
    assert zr.shape == (200,) and lab.shape == (200,)
    assert (lab == PEN_UP).any() and (lab != PEN_UP).any()


def test_no_pendown_sample_lies_on_a_connector():
    strokes = _two_strokes()
    z, seg, clen = join_labeled(strokes)
    zr, lab = resample_labeled(z, seg, 400, jump_time=0.05)
    lab = np.asarray(lab)
    assert all(_on_some_stroke(p, strokes) for p in zr[lab != PEN_UP])


def test_smoothstep_connector_has_zero_velocity_at_ends():
    z, seg, clen = join_labeled(_two_strokes())
    n = 2000
    zr, lab = resample_labeled(z, seg, n, jump_time=0.1)
    lab = np.asarray(lab)
    idx = np.where(lab == PEN_UP)[0]
    run = np.split(idx, np.where(np.diff(idx) != 1)[0] + 1)[0]
    assert len(run) >= 8
    vel = np.diff(zr[run])
    mid = abs(vel[len(vel) // 2])
    assert abs(vel[0]) < 0.5 * mid
    assert abs(vel[-1]) < 0.5 * mid


def _masked_pct(strokes, M, jump_time, N=2048):
    z, seg, clen = join_labeled(strokes)
    zr, lab = resample_labeled(z, seg, N, jump_time=jump_time)
    full = spectrum(zr)
    kept = select(full, M, "magnitude")
    return error(zr, full, kept, mask=(np.asarray(lab) != PEN_UP)).pct_height


def test_smooth_jump_beats_discontinuity_masked_error_at_M64():
    strokes = _two_strokes()
    assert _masked_pct(strokes, 64, 2 / 64) < _masked_pct(strokes, 64, 0.0)


def test_ac7_masked_error_bounds():
    strokes = _two_strokes()
    z, seg, clen = join_labeled(strokes)
    for M in (64, 256):
        zb = resample(z, 2048)
        fb = spectrum(zb)
        baseline = error(zb, fb, select(fb, M, "magnitude")).pct_height
        smooth = _masked_pct(strokes, M, 2 / M)
        zero = _masked_pct(strokes, M, 0.0)
        assert smooth <= zero + 1e-9
        assert smooth <= baseline + 1e-9


def test_error_mask_none_matches_v1():
    z = np.exp(2j * np.pi * np.arange(256) / 256)
    full = spectrum(z)
    kept = select(full, 3, "magnitude")
    assert error(z, full, kept).pct_height == error(z, full, kept, mask=None).pct_height


def test_json_segments_round_trip():
    z = np.exp(2j * np.pi * np.arange(256) / 256)
    kept = select(spectrum(z), 5, "magnitude")
    segs = [
        {"t0": 0.0, "t1": 0.4, "colour": [0, 0, 0]},
        {"t0": 0.5, "t1": 0.9, "colour": [255, 0, 0]},
    ]
    d = json.loads(to_json(kept, 256, "magnitude", segments=segs, background=[255, 255, 255]))
    assert d["segments"] == segs
    assert d["background"] == [255, 255, 255]
    # the v1 keys stay intact for old consumers
    assert d["N"] == 256 and len(d["terms"]) == 5
