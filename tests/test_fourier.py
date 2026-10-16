"""U1: discrete Fourier coefficients — ``dft_ref`` (reference) and ``spectrum``.

Contracts in docs/design.md#core/fourier.py and the math section:
  c_k = (1/N) Σ_n z_n e^{-2πi k n/N},  k ∈ [-⌊N/2⌋, ⌈N/2⌉-1], ascending.
"""
import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st
from hypothesis.extra.numpy import arrays

from epicycles.core.fourier import Spectrum, dft_ref, spectrum


def _circle(n: int, a: complex = 0.0, r: float = 1.0, clockwise: bool = False):
    j = np.arange(n)
    sign = -1.0 if clockwise else 1.0
    return a + r * np.exp(sign * 2j * np.pi * j / n)


def test_circle_single_term_k1():  # AC-1a
    n, a, r = 64, 3 - 2j, 2.5
    k, c = dft_ref(_circle(n, a, r))
    assert abs(c[k == 0][0] - a) < 1e-9 * r
    assert abs(abs(c[k == 1][0]) - r) < 1e-9 * r
    others = c[(k != 0) & (k != 1)]
    assert np.all(np.abs(others) < 1e-9 * r)


def test_clockwise_circle_is_k_minus_1():
    n, r = 64, 1.7
    k, c = dft_ref(_circle(n, 0, r, clockwise=True))
    assert abs(abs(c[k == -1][0]) - r) < 1e-9 * r
    assert np.all(np.abs(c[k != -1]) < 1e-9 * r)


def test_constant_only_k0():
    n = 32
    k, c = dft_ref(np.full(n, 4 - 1j, dtype=np.complex128))
    assert abs(c[k == 0][0] - (4 - 1j)) < 1e-12
    assert np.all(np.abs(c[k != 0]) < 1e-12)


@pytest.mark.parametrize("n", [4, 5, 7, 8, 16, 17])
def test_canonical_k_order_and_range(n):
    k, c = spectrum(np.zeros(n, dtype=np.complex128))
    assert k.dtype == np.int64
    assert k[0] == -(n // 2)
    assert k[-1] == n - n // 2 - 1
    assert np.all(np.diff(k) == 1)
    assert len(k) == n and len(c) == n


@given(
    arrays(
        np.complex128,
        st.integers(4, 64).map(lambda n: (n,)),
        elements=st.complex_numbers(
            max_magnitude=1e3, allow_nan=False, allow_infinity=False
        ),
    )
)
def test_spectrum_matches_dft_ref(z):
    kr, cr = dft_ref(z)
    kf, cf = spectrum(z)
    assert np.array_equal(kr, kf)
    scale = max(float(np.max(np.abs(z))), 1e-12)
    assert np.allclose(cf, cr, atol=1e-10 * scale, rtol=0)


def test_translation_shifts_only_c0():
    n, a = 48, 5 - 3j
    base = _circle(n, 0, 2.0)
    k, c = dft_ref(base)
    k2, c2 = dft_ref(base + a)
    assert abs((c2[k2 == 0][0] - c[k == 0][0]) - a) < 1e-9
    mask = k != 0
    assert np.allclose(c2[mask], c[mask], atol=1e-9)


def test_spectrum_returns_spectrum_type():
    spec = spectrum(_circle(8))
    assert isinstance(spec, Spectrum)
