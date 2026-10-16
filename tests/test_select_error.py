"""U3: term selection and reconstruction error.

Contracts in docs/design.md#core/fourier.py and the math section:
  select(spec, m, mode): m terms incl k=0; k=0 first; magnitude sorts remaining
    by (-|c|, |k|, k), frequency by (|k|, k); returned in selection order.
  error(z, full, kept) -> ErrorReport{rms_sampled, rms_parseval, pct_height};
    sampled == parseval (rtol 1e-9, atol 1e-12*max|z|); pct over max(w,h);
    zero-size bbox raises ValueError.
"""
import numpy as np
import pytest
from hypothesis import assume, given
from hypothesis import strategies as st
from hypothesis.extra.numpy import arrays

from epicycles.core.fourier import (
    ErrorReport,
    Spectrum,
    error,
    select,
    spectrum,
)


def _tie_spec() -> Spectrum:
    # |c|: k=0 ->5, k=1 ->3, k=-1 ->3 (tie), k=2 ->2, k=-2 ->1
    k = np.array([-2, -1, 0, 1, 2], dtype=np.int64)
    c = np.array([1.0, 3.0, 5.0, 3.0, 2.0], dtype=np.complex128)
    return Spectrum(k, c)


def test_magnitude_ordering_with_tiebreak():
    sel = select(_tie_spec(), 5, "magnitude")
    # k=0 first; then |c|=3 tie broken by |k| then k (-1 before 1); then 2, -2
    assert list(sel.k) == [0, -1, 1, 2, -2]


def test_frequency_ordering():
    sel = select(_tie_spec(), 5, "frequency")
    assert list(sel.k) == [0, -1, 1, -2, 2]


@pytest.mark.parametrize("m", [1, 2, 3, 5])
def test_k0_first_and_counted_in_m(m):
    sel = select(_tie_spec(), m, "magnitude")
    assert sel.k[0] == 0
    assert len(sel.k) == m


def _nontrivial_path(n: int) -> np.ndarray:
    j = np.arange(n)
    return (
        (1 - 1j)
        + 2.0 * np.exp(2j * np.pi * j / n)
        + 0.7 * np.exp(-4j * np.pi * j / n)
        + 0.3 * np.exp(6j * np.pi * j / n)
    )


def test_m_equals_n_near_zero_error():
    z = _nontrivial_path(32)
    full = spectrum(z)
    kept = select(full, 32, "magnitude")
    rep = error(z, full, kept)
    scale = max(np.ptp(z.real), np.ptp(z.imag))
    assert rep.rms_sampled < 1e-9 * scale


def test_rms_nonincreasing_in_m():
    z = _nontrivial_path(32)
    full = spectrum(z)
    prev = np.inf
    for m in range(1, 33):
        rep = error(z, full, select(full, m, "magnitude"))
        assert rep.rms_parseval <= prev + 1e-12
        prev = rep.rms_parseval


def test_percent_uses_max_dimension():
    z = _nontrivial_path(24)
    full = spectrum(z)
    kept = select(full, 3, "magnitude")
    rep = error(z, full, kept)
    w, h = np.ptp(z.real), np.ptp(z.imag)
    assert w != h  # guard: the test only means something if dims differ
    assert np.isclose(rep.pct_height, 100.0 * rep.rms_sampled / max(w, h))
    assert not np.isclose(rep.pct_height, 100.0 * rep.rms_sampled / min(w, h))
    assert isinstance(rep, ErrorReport)


def test_zero_bbox_raises():
    z = np.full(8, 2 + 3j, dtype=np.complex128)
    full = spectrum(z)
    with pytest.raises(ValueError):
        error(z, full, select(full, 1, "magnitude"))


@given(
    arrays(
        np.complex128,
        st.integers(4, 32).map(lambda n: (n,)),
        elements=st.complex_numbers(
            max_magnitude=1e3, allow_nan=False, allow_infinity=False
        ),
    ),
    st.integers(1, 32),
)
def test_sampled_equals_parseval(z, m):
    n = len(z)
    w, h = np.ptp(z.real), np.ptp(z.imag)
    assume(max(w, h) > 1e-6)
    full = spectrum(z)
    kept = select(full, min(m, n), "magnitude")
    rep = error(z, full, kept)
    maxz = max(float(np.max(np.abs(z))), 1e-12)
    assert np.isclose(
        rep.rms_sampled, rep.rms_parseval, rtol=1e-9, atol=1e-12 * maxz
    )
