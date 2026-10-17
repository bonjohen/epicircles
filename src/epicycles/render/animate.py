"""Render an epicycle animation to GIF (or MP4 if ffmpeg is available).

I/O only. Draws, per frame: the circle for each term (radii below 0.5 px on
screen are skipped), the radius-vector chain from the anchor to the pen, the
accumulated pen trail, and optionally the faint original path. Geometry comes
from :func:`epicycles.render.frames.frame_geometry`; this module only plots it.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless; no display required

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.animation import FuncAnimation, PillowWriter  # noqa: E402
from matplotlib.patches import Circle  # noqa: E402

from epicycles.core.fourier import Spectrum  # noqa: E402
from epicycles.core.tour import PEN_UP  # noqa: E402
from epicycles.render.frames import (  # noqa: E402
    frame_geometry,
    pen_path,
    trail_labels,
    trail_resolution,
)


def write_animation(
    spec: Spectrum,
    out_path: str | Path,
    n_frames: int = 600,
    fps: int = 30,
    original: np.ndarray | None = None,
    labels: np.ndarray | None = None,
) -> Path:
    """Write an animated GIF of the epicycle reconstruction to ``out_path``.

    When ``labels`` (the per-sample tour labels from ``resample_labeled``) is
    given, the dense trail is **broken at ``PEN_UP`` points** so connector spans
    are traversed by the arm but not drawn (the pen lifts). See docs/design.md
    §P6.
    """
    out_path = Path(out_path)
    geoms = frame_geometry(spec, n_frames)

    # Dense pen trail, sampled by term count (not n_frames), revealed over time.
    n_samples = 0 if original is None else len(original)
    resolution = trail_resolution(len(spec.c), n_samples)
    pen = pen_path(spec, resolution)

    # Pen-up: NaN out the trail where the sample label is PEN_UP, so matplotlib
    # leaves a gap (the arm still moves, the trail is not drawn there).
    pen_draw = pen.astype(np.complex128).copy()
    if labels is not None:
        up = trail_labels(labels, resolution) == PEN_UP
        pen_draw[up] = np.nan + 1j * np.nan

    pts = pen if original is None else np.concatenate([pen, original])
    # No padding: the drawing fills the frame edge-to-edge.
    xlim = (float(pts.real.min()), float(pts.real.max()))
    ylim = (float(pts.imag.min()), float(pts.imag.max()))

    # Figure matches the drawing's aspect and the axes fill it completely, so
    # the reconstruction reaches every edge with no surrounding margin.
    w = xlim[1] - xlim[0] or 1.0
    h = ylim[1] - ylim[0] or 1.0
    base = 6.0
    fig = plt.figure(figsize=(base * w / h, base))
    ax = fig.add_axes((0.0, 0.0, 1.0, 1.0))
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)

    if original is not None:
        ax.plot(original.real, original.imag, lw=0.5, alpha=0.2, color="tab:blue")

    # Minimum drawable radius: 0.5 px converted to data units. Approximate —
    # uses the axes' current px/data width and assumes square-ish scaling.
    fig.canvas.draw()
    px_per_data = ax.get_window_extent().width / (xlim[1] - xlim[0])
    min_radius = 0.5 / px_per_data if px_per_data > 0 else 0.0

    m_minus_1 = len(geoms[0].centers)
    circles = [
        Circle((0, 0), 0.0, fill=False, lw=0.4, color="0.6", visible=False)
        for _ in range(m_minus_1)
    ]
    for c in circles:
        ax.add_patch(c)
    (radius_line,) = ax.plot([], [], lw=0.5, color="0.4")
    (trail,) = ax.plot([], [], lw=1.5, color="tab:red")

    def update(i: int):
        g = geoms[i]
        for c, centre, r in zip(circles, g.centers, g.radii):
            if r >= min_radius:
                c.center = (centre.real, centre.imag)
                c.radius = r
                c.set_visible(True)
            else:
                c.set_visible(False)
        chain_pts = np.append(g.centers, g.pen)
        radius_line.set_data(chain_pts.real, chain_pts.imag)
        # reveal the dense trail up to this frame's time t=(i+1)/n_frames
        shown = round((i + 1) / n_frames * resolution)
        trail.set_data(pen_draw.real[:shown], pen_draw.imag[:shown])
        return (*circles, radius_line, trail)

    anim = FuncAnimation(fig, update, frames=n_frames, blit=False)
    anim.save(str(out_path), writer=PillowWriter(fps=fps))
    plt.close(fig)
    return out_path
