# Demo animations (one per input type)

Committed so the epicycle output can be reviewed from GitHub without running the
tool. All sources are public domain; each GIF is < 5 MB. Regenerate with the
commands below (the pen trail is dense/F7.1, so these are smooth).

| GIF | Input type | Source | Licence | Result |
|---|---|---|---|---|
| `clef_svg.gif` | SVG | Wikimedia `File:Treble_clef.svg` — `https://upload.wikimedia.org/wikipedia/commons/f/fa/Treble_clef.svg` | Public domain | N=2048, 9 strokes, 0.086% @ M=256 |
| `crab_lineart.gif` | raster line art | Wikimedia `File:Crab_Drawing.png` (Jessie Wilcox Smith, 1916) — `https://upload.wikimedia.org/wikipedia/commons/1/11/Crab_Drawing.png` | Public domain (PD-1923) | N=16384, 166 strokes, 1.28% @ M=256 |
| `earth_photo.gif` | photo | Wikimedia `File:The_Earth_seen_from_Apollo_17.jpg` (NASA, Apollo 17, 1972) — `https://upload.wikimedia.org/wikipedia/commons/9/97/The_Earth_seen_from_Apollo_17.jpg` | Public domain (NASA) | N=16384, 44 strokes, 0.74% @ M=400 |

## Regenerate

```
# SVG
python -m epicycles draw "https://upload.wikimedia.org/wikipedia/commons/f/fa/Treble_clef.svg" \
    --terms 256 --frames 100 --fps 25 --out demo/clef_svg.gif

# raster line art (auto-detected as lineart)
python -m epicycles draw "https://upload.wikimedia.org/wikipedia/commons/1/11/Crab_Drawing.png" \
    --terms 256 --frames 100 --fps 25 --out demo/crab_lineart.gif

# photo (Canny edge filters exercised from the CLI)
python -m epicycles draw "https://upload.wikimedia.org/wikipedia/commons/9/97/The_Earth_seen_from_Apollo_17.jpg" \
    --kind photo --max-dim 360 --sigma 2.5 --low 0.08 --high 0.18 \
    --min-component 40 --spur 6 --terms 400 --frames 100 --fps 25 --out demo/earth_photo.gif
```
