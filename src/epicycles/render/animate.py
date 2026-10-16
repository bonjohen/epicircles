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
from epicycles.render.frames import frame_geometry  # noqa: E402


def write_animation(
    spec: Spectrum,
    out_path: str | Path,
    n_frames: int = 600,
    fps: int = 30,
    original: np.ndarray | None = None,
) -> Path:
    """Write an animated GIF of the epicycle reconstruction to ``out_path``."""
    out_path = Path(out_path)
    geoms = frame_geometry(spec, n_frames)
    pens = np.array([g.pen for g in geoms], dtype=np.complex128)

    pts = pens if original is None else np.concatenate([pens, original])
    pad = 0.05 * max(float(np.ptp(pts.real)), float(np.ptp(pts.imag)), 1.0)
    xlim = (pts.real.min() - pad, pts.real.max() + pad)
    ylim = (pts.imag.min() - pad, pts.imag.max() + pad)

    fig, ax = plt.subplots()
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)

    if original is not None:
        ax.plot(original.real, original.imag, lw=0.5, alpha=0.2, color="tab:blue")

    # Minimum drawable radius: 0.5 px converted to data units.
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

    trail_x: list[float] = []
    trail_y: list[float] = []

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
        trail_x.append(g.pen.real)
        trail_y.append(g.pen.imag)
        trail.set_data(trail_x, trail_y)
        return (*circles, radius_line, trail)

    anim = FuncAnimation(fig, update, frames=n_frames, blit=False)
    anim.save(str(out_path), writer=PillowWriter(fps=fps))
    plt.close(fig)
    return out_path
