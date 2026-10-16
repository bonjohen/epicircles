"""Discrete Fourier transform of a closed complex path.

A path sample is a complex number ``x + iy``. For ``N`` samples ``z_n`` the
Fourier coefficients are

    c_k = (1/N) Σ_{n=0}^{N-1} z_n e^{-2πi k n / N},   k ∈ [-⌊N/2⌋, ⌈N/2⌉-1].

Coefficients are returned in **canonical order**: ``k`` ascending and
contiguous. See docs/design.md#core/fourier.py.
"""
from __future__ import annotations

from typing import NamedTuple

import numpy as np


class Spectrum(NamedTuple):
    """Frequencies and coefficients, paired elementwise.

    ``k`` and ``c`` have the same length ``N``. The canonical order produced by
    :func:`dft_ref` / :func:`spectrum` has ``k`` ascending; later operations
    (e.g. ``select``) may reorder the pair while keeping the pairing.
    """

    k: np.ndarray  # int64, shape (N,)
    c: np.ndarray  # complex128, shape (N,)


def _canonical_k(n: int) -> np.ndarray:
    """Ascending, contiguous frequencies ``[-⌊N/2⌋ … ⌈N/2⌉-1]`` as int64."""
    return np.arange(-(n // 2), n - n // 2, dtype=np.int64)


def dft_ref(z: np.ndarray) -> Spectrum:
    """O(N²) reference transform (tests only).

    Directly evaluates the definition sum for every canonical ``k``.
    """
    z = np.asarray(z, dtype=np.complex128)
    n = z.shape[0]
    k = _canonical_k(n)
    j = np.arange(n)
    # basis[i, m] = e^{-2πi k_i m / N}; c = (basis @ z) / N.
    basis = np.exp(-2j * np.pi * np.outer(k, j) / n)
    c = (basis @ z) / n
    return Spectrum(k, c.astype(np.complex128))


def spectrum(z: np.ndarray) -> Spectrum:
    """Fast transform: ``numpy.fft.fft(z)/N`` reindexed to canonical order.

    Matches :func:`dft_ref` to ``1e-10·max|z|``.
    """
    z = np.asarray(z, dtype=np.complex128)
    n = z.shape[0]
    c = np.fft.fftshift(np.fft.fft(z)) / n
    return Spectrum(_canonical_k(n), c.astype(np.complex128))
