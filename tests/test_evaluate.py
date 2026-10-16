"""U2: path reconstruction — ``evaluate`` (any order) and ``chain`` (selection).

Contracts in docs/design.md#core/fourier.py:
  evaluate(spec, t) = Σ_k c_k e^{2πi k t}            (t an array; order-free)
  chain(spec, t)    = cumulative partial sums in selection order; k=0 must be
                      first; chain[0]=c_0, chain[-1]=evaluate(spec,[t])[0].
"""
import numpy as np
import pytest

from epicycles.core.fourier import Spectrum, chain, evaluate, spectrum


def _circle(n, a=0.0, r=1.0):
    j = np.arange(n)
    return a + r * np.exp(2j * np.pi * j / n)


def test_full_spectrum_reproduces_samples():
    n = 50
    z = _circle(n, 1 - 1j, 2.0) + 0.3 * np.exp(6j * np.pi * np.arange(n) / n)
    spec = spectrum(z)
    t = np.arange(n) / n
    assert np.allclose(evaluate(spec, t), z, atol=1e-9)


def test_chain_shape_anchor_and_pen():
    # Hand-built selection-order spectrum with k=0 first.
    k = np.array([0, 1, -1, 2], dtype=np.int64)
    c = np.array([1 + 1j, 2.0, 0.5j, -0.3], dtype=np.complex128)
    spec = Spectrum(k, c)
    t = 0.137
    ch = chain(spec, t)
    assert ch.shape == (len(k),)
    assert ch[0] == c[0]  # anchor = c_0 (k=0 term does not rotate)
    assert np.isclose(ch[-1], evaluate(spec, np.array([t]))[0], atol=1e-12)


def test_chain_is_cumulative_partial_sums():
    k = np.array([0, 1, -1], dtype=np.int64)
    c = np.array([2.0, 1.0, 0.5], dtype=np.complex128)
    spec = Spectrum(k, c)
    t = 0.25
    terms = c * np.exp(2j * np.pi * k * t)
    assert np.allclose(chain(spec, t), np.cumsum(terms), atol=1e-12)


def test_chain_requires_k0_first():
    k = np.array([1, 0, -1], dtype=np.int64)  # k=0 NOT first
    c = np.array([1.0, 2.0, 0.5], dtype=np.complex128)
    with pytest.raises(ValueError):
        chain(Spectrum(k, c), 0.0)


def test_ellipse_from_k_plus_minus_one():
    # z(t) = A e^{2πit} + B e^{-2πit} = (A+B)cos + i(A-B)sin
    a_coef, b_coef = 3.0, 1.0
    k = np.array([0, 1, -1], dtype=np.int64)
    c = np.array([0.0, a_coef, b_coef], dtype=np.complex128)
    spec = Spectrum(k, c)
    t = np.linspace(0, 1, 2001, endpoint=False)
    z = evaluate(spec, t)
    assert np.isclose(np.max(z.real), a_coef + b_coef, atol=1e-3)
    assert np.isclose(np.max(z.imag), a_coef - b_coef, atol=1e-3)
