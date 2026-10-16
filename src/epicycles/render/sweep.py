"""Static grid of reconstructions for a list of term counts M.

``sweep_traces`` is pure (returns the (m, trace) data); ``write_sweep`` lays the
traces out in a grid PNG. Each panel is the ``evaluate`` trace of the top-m
terms selected from the full spectrum.
"""
from __future__ import annotations

from math import ceil
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from epicycles.core.fourier import Spectrum, evaluate, select  # noqa: E402


def sweep_traces(
    full: Spectrum,
    terms: list[int],
    order: str = "magnitude",
    n_points: int = 2000,
) -> list[tuple[int, np.ndarray]]:
    """Return ``[(m, trace)]`` where trace = evaluate(select(full, m), t)."""
    t = np.linspace(0.0, 1.0, n_points, endpoint=False)
    return [(m, evaluate(select(full, m, order), t)) for m in terms]


def write_sweep(
    full: Spectrum,
    terms: list[int],
    out_path: str | Path,
    order: str = "magnitude",
    n_points: int = 2000,
) -> Path:
    """Write a grid PNG with one reconstruction panel per term count."""
    out_path = Path(out_path)
    traces = sweep_traces(full, terms, order, n_points)
    k = len(traces)
    ncols = min(k, 4)
    nrows = ceil(k / ncols)
    fig, axes = plt.subplots(nrows, ncols, figsize=(3 * ncols, 3 * nrows), squeeze=False)
    flat = axes.ravel()
    for ax, (m, z) in zip(flat, traces):
        ax.plot(z.real, z.imag, lw=0.8, color="tab:red")
        # a degenerate panel (e.g. M=1 is just c_0, a single point) draws nothing
        # with a line alone; mark it with a dot so the panel isn't blank.
        if np.ptp(z.real) < 1e-9 and np.ptp(z.imag) < 1e-9:
            ax.plot(z.real[:1], z.imag[:1], marker="o", ms=4, color="tab:red")
        ax.set_aspect("equal")
        ax.axis("off")
        ax.set_title(f"M={m}")
    for ax in flat[k:]:
        ax.axis("off")
    fig.tight_layout()
    fig.savefig(out_path, dpi=100)
    plt.close(fig)
    return out_path
