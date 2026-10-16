# epicycles

Fourier-epicycle line drawing: convert a drawing (SVG, line-art raster, or
photo) into a single closed path, compute its discrete Fourier transform, and
animate the reconstruction as a chain of rotating vectors (epicycles).

See `docs/requirements.md`, `docs/design.md`, and `docs/plan.md`.

## Usage

```
python -m epicycles --help
python -m epicycles draw <svg|png|url> --terms 256 --out out.gif --json coeffs.json
python -m epicycles sweep <src> --terms 1,4,16,64,256 --out grid.png
python -m epicycles info  <src>
```

Raster line art and photos: add `--kind lineart|photo` (or let `--kind auto`
decide by ink fraction); photo edge filters are `--sigma/--low/--high` and
`--min-component/--spur/--max-dim`.

## Browser renderer

`web/index.html` animates a `coeffs.json` on a canvas with an M-terms slider.
Serve the folder over HTTP so `fetch` can read the JSON:

```
cd web && python -m http.server 8000   # then open http://localhost:8000/
```

A demo `web/coeffs.json` (the ethanol fixture) is included; regenerate it for
any drawing with `... draw <src> --json web/coeffs.json`.
