"""U15: prune small components and short spurs.

Contract in docs/design.md#core/raster.py: prune(skel, min_component_px,
spur_len) drops 8-connected components smaller than min_component_px and removes
dead-end branches shorter than spur_len; the main line is untouched.
"""
import numpy as np

from epicycles.core.raster import prune


def _line_with_spur():
    m = np.zeros((20, 50), dtype=bool)
    m[10, 5:46] = True  # horizontal line, 41 px
    m[7:10, 25] = True  # vertical spur rows 7,8,9 (3 px) joining at (10,25)
    return m


def test_short_spur_removed_main_line_kept():
    out = prune(_line_with_spur(), min_component_px=1, spur_len=5)
    assert not out[7, 25] and not out[8, 25] and not out[9, 25]  # spur gone
    assert out[10, 5:46].all()  # main line intact


def test_small_component_removed():
    m = np.zeros((20, 50), dtype=bool)
    m[10, 5:46] = True  # 41 px line
    m[2, 2] = True
    m[2, 3] = True  # 2 px blob
    out = prune(m, min_component_px=10, spur_len=1)
    assert out[10, 5:46].all()
    assert not out[2, 2] and not out[2, 3]


def test_long_branch_not_removed():
    m = np.zeros((20, 50), dtype=bool)
    m[10, 5:46] = True
    m[2:10, 25] = True  # vertical branch of length 8 (>= spur_len)
    out = prune(m, min_component_px=1, spur_len=5)
    assert out[2:10, 25].all()  # long branch kept
    assert out[10, 5:46].all()
