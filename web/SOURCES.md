# Demo asset sources and regeneration

The committed demo assets (`coeffs.json`, `original.png`, `original.json`) are a
convenience so the renderer works out of the box.

**Currently committed demo: `me3` portrait.** The live `coeffs.json` /
`original.png` / `original.json` are John Boen's own line-art portrait (same
image as `tests/fixtures/me3.png`, used with permission), cropped to the circle.
The coefficients were generated during development by the clean line-art pipeline
(skeleton → prune short strokes → weld near-touching endpoints → 2-opt/Or-opt
order → DFT, M=4000); that path is not yet exposed on the CLI (lands with U20
wiring), so this asset is not CLI-reproducible yet. `original.json` is the pixel
frame `{x:0, y:H, w:W, h:H}` of `load_gray(me3_crop.png, 800)`.

The public-domain treble-clef source below is retained for reference and remains
reproducible via the CLI.

## Source drawing (reference)

| File | Source | Licence |
|---|---|---|
| me3 portrait | John Boen, own image, used with permission | Used with permission (repo owner) |
| treble clef | Wikimedia Commons, `File:Treble clef.svg` — page `https://commons.wikimedia.org/wiki/File:Treble_clef.svg`, file `https://upload.wikimedia.org/wikipedia/commons/f/fa/Treble_clef.svg` | **Public domain** (author released worldwide into the public domain) |

## Regenerate `coeffs.json` (the animated coefficients)

M = 512 terms, N = 2048 samples (the `draw` default for SVG), magnitude order:

```
python -m epicycles draw "https://upload.wikimedia.org/wikipedia/commons/f/fa/Treble_clef.svg" \
    --terms 512 --json web/coeffs.json
```

## Regenerate `original.png` + `original.json` (the 10% backdrop)

The clef is a vector source, so the backdrop is the clef's own strokes
rasterized to a frame whose pixel extent **equals the stroke bounding box** (so
it registers exactly with the reconstruction). `original.json` records that box
as `{x, y, w, h}` with `(x, y)` the top-left corner in y-up drawing coords:

```python
import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from epicycles.io.fetch import fetch
from epicycles.io.svg import load_svg

src = "https://upload.wikimedia.org/wikipedia/commons/f/fa/Treble_clef.svg"
strokes = load_svg(fetch(src, __import__("pathlib").Path(".cache")), 8192)
allp = np.concatenate(strokes)
minx, maxx = float(allp.real.min()), float(allp.real.max())
miny, maxy = float(allp.imag.min()), float(allp.imag.max())
w, h = maxx - minx, maxy - miny

px_h = 1000
fig = plt.figure(figsize=(px_h * w / h / 100.0, px_h / 100.0), dpi=100)
ax = fig.add_axes([0, 0, 1, 1]); ax.set_axis_off()
ax.set_xlim(minx, maxx); ax.set_ylim(miny, maxy)
for s in strokes:
    ax.plot(s.real, s.imag, color="white", linewidth=2.0, solid_capstyle="round")
fig.savefig("web/original.png", transparent=True, dpi=100)
json.dump({"x": minx, "y": maxy, "w": w, "h": h}, open("web/original.json", "w"))
```

For a **raster/photo** source instead, the backdrop is the source image itself
and `original.json` is its pixel frame `{x:0, y:H, w:W, h:H}` where `W×H` are the
`load_gray(..., max_dim)` dimensions (pixel `(row,col) → x=col+0.5, y=H-row-0.5`).
