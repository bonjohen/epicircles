"""Discrete Fourier transform of a closed complex path.

A path sample is a complex number ``x + iy``. For ``N`` samples ``z_n`` the
Fourier coefficients are

    c_k = (1/N) Σ_{n=0}^{N-1} z_n e^{-2πi k n / N},   k ∈ [-⌊N/2⌋, ⌈N/2⌉-1].

Coefficients are returned in **canonical order**: ``k`` ascending and
contiguous. See docs/design.md#core/fourier.py.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, NamedTuple

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


def evaluate(spec: Spectrum, t: np.ndarray) -> np.ndarray:
    """Reconstruct the path at parameters ``t``.

    ``ẑ(t) = Σ_k c_k e^{2πi k t}`` for each ``t`` (sample ``n`` ↔ ``t=n/N``).
    Order-independent: the sum is over all terms regardless of their arrangement
    in ``spec``.
    """
    t = np.asarray(t, dtype=np.float64)
    # phase[i, j] = e^{2πi k_j t_i};  result[i] = Σ_j c_j phase[i, j].
    phase = np.exp(2j * np.pi * np.outer(t, spec.k))
    return phase @ spec.c


def chain(spec: Spectrum, t: float) -> np.ndarray:
    """Cumulative partial sums of the rotating terms at a single ``t``.

    Returns ``m`` points in selection order: ``chain[0]`` is the anchor ``c_0``
    (the k=0 term does not rotate), ``chain[j]`` is the centre of circle
    ``j+1``, and ``chain[-1]`` is the pen position ``evaluate(spec, [t])[0]``.

    Requires ``spec.k[0] == 0`` (i.e. a ``select`` result); raises
    :class:`ValueError` otherwise.
    """
    if spec.k.shape[0] == 0 or spec.k[0] != 0:
        raise ValueError("chain requires the k=0 term at index 0 (a select result)")
    terms = spec.c * np.exp(2j * np.pi * spec.k * float(t))
    return np.cumsum(terms)


def select(spec: Spectrum, m: int, mode: Literal["magnitude", "frequency"]) -> Spectrum:
    """Keep ``m`` terms including ``k=0``, returned in drawing order.

    ``k=0`` is always first (for ``m >= 1``). The remaining ``m-1`` terms are
    chosen and ordered by ``mode``:

    * ``magnitude`` — by ``(-|c|, |k|, k)``: largest magnitude first, ties
      broken by frequency distance then signed frequency.
    * ``frequency`` — by ``(|k|, k)``: lowest frequencies first.
    """
    zero = np.where(spec.k == 0)[0]
    if zero.size == 0:
        raise ValueError("select requires a k=0 term in the spectrum")
    rest = np.where(spec.k != 0)[0]
    kr = spec.k[rest]
    if mode == "magnitude":
        order = np.lexsort((kr, np.abs(kr), -np.abs(spec.c[rest])))
    elif mode == "frequency":
        order = np.lexsort((kr, np.abs(kr)))
    else:
        raise ValueError(f"unknown mode {mode!r}")
    take = max(int(m) - 1, 0)
    chosen = rest[order][:take]
    idx = np.concatenate(([zero[0]], chosen))
    return Spectrum(spec.k[idx], spec.c[idx])


@dataclass
class ErrorReport:
    """Reconstruction error of a kept term set against the samples."""

    rms_sampled: float
    rms_parseval: float
    pct_height: float


def error(
    z: np.ndarray,
    full: Spectrum,
    kept: Spectrum,
    mask: np.ndarray | None = None,
) -> ErrorReport:
    """Reconstruction error of ``kept`` terms over the samples ``z``.

    ``rms_sampled`` is the RMS pointwise distance at ``t=n/N``; ``rms_parseval``
    is ``sqrt(Σ_{k∉kept} |c_k|²)`` (dropped energy). With ``mask=None`` the two
    agree up to float error. ``pct_height`` is ``100·rms_sampled / max(width,
    height)`` of the sample bounding box; a zero-size bounding box raises
    :class:`ValueError`.

    When ``mask`` (a boolean ``(n,)``, typically ``label != PEN_UP``) is given,
    ``rms_sampled`` and ``pct_height`` are computed over the **pen-down samples
    only** (FR-13). Parseval no longer applies to that masked rms, so
    ``rms_parseval`` stays the unmasked value as an internal consistency check.
    """
    z = np.asarray(z, dtype=np.complex128)
    n = z.shape[0]
    t = np.arange(n) / n
    resid2 = np.abs(z - evaluate(kept, t)) ** 2

    dropped = ~np.isin(full.k, kept.k)
    rms_parseval = float(np.sqrt(np.sum(np.abs(full.c[dropped]) ** 2)))

    sel = np.ones(n, dtype=bool) if mask is None else np.asarray(mask, dtype=bool)
    if not sel.any():
        raise ValueError("no pen-down samples to measure")
    rms_sampled = float(np.sqrt(np.mean(resid2[sel])))

    zp = z[sel]
    scale = max(float(np.ptp(zp.real)), float(np.ptp(zp.imag)))
    if scale == 0.0:
        raise ValueError("degenerate (zero-size) bounding box; percent undefined")
    pct_height = 100.0 * rms_sampled / scale
    return ErrorReport(rms_sampled, rms_parseval, pct_height)
