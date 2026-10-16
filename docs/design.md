# Design — epicycles

## Pipeline
```
source ──fetch──► file ──load──► strokes ──join──► tour ──resample──► z[N]
                                                                      │
             frames ◄──render── chain(t) ◄──select M── (k, c) ◄──dft──┘
```
Every arrow left of `render` is a pure function in `core/` except `fetch`/`load` (`io/`).

## Coordinates and types
- A point is a complex number `x + iy`, **y up**. The SVG loader negates y (`y_up = -y_svg`), which works for any viewBox origin. The image loader uses pixel centres (`y = H - row - 0.5`).
- `Stroke`: `np.ndarray[complex128]`, shape `(m,)`, m ≥ 2, open polyline, no implied closure.
- `Tour`: `np.ndarray[complex128]`, shape `(n,)`, closed (last point connects to first; first point is **not** repeated at the end).
- `Spectrum`: `(k: np.ndarray[int64] (N,), c: np.ndarray[complex128] (N,))`, canonical order = k ascending.
- No normalisation of scale in core; units are input units (SVG user units or pixels).

## Math
- Coefficients: `c_k = (1/N) Σ_{n=0}^{N-1} z_n e^{-2πi k n/N}`, `k ∈ [-⌊N/2⌋, ⌈N/2⌉-1]`.
- Reconstruction: `ẑ(t) = Σ_{k∈S} c_k e^{2πi k t}`, `t ∈ [0,1)`. Sample n ↔ `t = n/N`.
- Each term is an epicycle: radius `|c_k|`, phase `arg c_k`, k turns per period (k<0 clockwise). `c_0` = centroid of the samples. It does not rotate, so it is the chain's anchor point, not a drawn circle. m counts the k=0 term.
- Error with term set S over the samples:
  - sampled: `rms = sqrt(mean |z_n - ẑ(n/N)|²)`
  - Parseval: `rms = sqrt(Σ_{k∉S} |c_k|²)` — identical up to float error.
  - percent: `100 · rms / max(width, height)` of the sample bounding box; if both are 0, raise `ValueError`.
  - The two rms values are compared with `rtol=1e-9, atol=1e-12·max|z|` (an rms near 0 at m=N makes a pure relative test meaningless).
- Arc-length resampling makes coefficients depend on geometry only (constant pen speed). Pen order and direction still change the spectrum; that is accepted and documented, not hidden.

## Modules and contracts

### `core/path.py`
| fn | signature | contract |
|---|---|---|
| `arc_length` | `(tour) -> np.ndarray[float] (n+1,)` | cumulative length including closing segment; `[0]=0` |
| `resample` | `(tour, n:int) -> Tour` | n points uniform in arc length, starting at `tour[0]`; raises `ValueError` if total length = 0 |

### `core/fourier.py`
| fn | signature | contract |
|---|---|---|
| `dft_ref` | `(z) -> Spectrum` | O(N²) reference; tests only |
| `spectrum` | `(z) -> Spectrum` | `numpy.fft.fft(z)/N`, reindexed to canonical order; matches `dft_ref` to 1e-10·max|z| |
| `select` | `(spec, m:int, mode:"magnitude"\|"frequency") -> Spectrum` | m terms including k=0. k=0 always first (for m≥1); the remaining m−1 by mode. magnitude: sort by (−\|c\|, \|k\|, k). frequency: sort by (\|k\|, k). Returned in selection order — the drawing order of the chain |
| `evaluate` | `(spec, t: np.ndarray[float]) -> np.ndarray[complex]` | `Σ c e^{2πikt}` for each t |
| `chain` | `(spec, t: float) -> np.ndarray[complex] (m,)` | partial sums in selection order. `chain[0] = c_0` (anchor), `chain[j]` = centre of circle j+1, `chain[-1] == evaluate(spec,[t])[0]` (pen). Raises `ValueError` unless k=0 is at index 0 (i.e. a `select` result) |
| `error` | `(z, full:Spectrum, kept:Spectrum) -> ErrorReport` | dataclass `{rms_sampled, rms_parseval, pct_height}` |

### `core/tour.py`
| fn | signature | contract |
|---|---|---|
| `join_strokes` | `(strokes: list[Stroke]) -> (Tour, connector_len: float)` | greedy: start with stroke 0; repeatedly append the unused stroke whose either endpoint is nearest the current end (reversing if needed); ties → lowest index, then forward orientation. Concatenate points; closing segment implied. connector_len = sum of joins + the closing jump (last point → first point). A stroke whose last point equals its first (within 1e-9·scale) has that duplicate dropped and contributes 0 closing length |
| `two_opt` (P5) | `(strokes order) -> order` | optional improvement; deterministic |

### `core/raster.py`
| fn | signature | contract |
|---|---|---|
| `binarize` | `(gray: uint8 HxW, threshold:int\|None) -> bool HxW` | True = ink. None → Otsu. Ink = darker than threshold |
| `edges` | `(gray, sigma, low, high) -> bool HxW` | converts to float in [0,1] (`skimage.util.img_as_float`), then `skimage.feature.canny(sigma, low_threshold=low, high_threshold=high)`. Thresholds are absolute gradient values on that [0,1] scale |
| `skeleton` | `(mask) -> bool HxW` | `skimage.morphology.skeletonize` |
| `prune` | `(skel, min_component_px:int, spur_len:int) -> bool HxW` | drop small 8-connected components; remove end-branches shorter than spur_len |
| `skeleton_to_strokes` | `(skel) -> list[Stroke]` | one stroke per 8-connected component: DFS closed walk over the pixel graph (each tree edge traversed out and back), **iterative with an explicit stack**, start = lowest (row, col) pixel, neighbour order fixed (N, NE, E, SE, S, SW, W, NW). Visits every pixel; consecutive points 8-adjacent; the final return to the start is not repeated. A tree of p pixels yields 2(p−1) points. Pixel centre → `x=col+0.5`, `y=H-row-0.5` |

DFS retrace doubles path length but always yields a valid closed walk; that is the v1 choice. The cost: the DFS tree drops loop edges, so a closed loop (e.g. a rectangle outline) is also traversed out and back, drawing it twice. Euler-path extraction with minimal duplication (U18) removes this.

### `io/fetch.py`
`fetch(src: str, cache_dir: Path) -> Path` — local path passthrough; URL → `cache_dir/sha256(url)[:16] + ext`, downloaded via `urllib.request` once, with a User-Agent header (Wikimedia rejects requests without one). `ext` from the URL path; if absent, from Content-Type (`image/svg+xml`→`.svg`, `image/png`→`.png`, `image/jpeg`→`.jpg`; anything else raises). No retries.

### `io/svg.py`
`load_svg(path, samples_per_unit: float) -> list[Stroke]` — `svgpathtools.Document(path).flatten_all_paths()` so group and element `transform`s are applied (plain `svg2paths` ignores them, and most web clipart uses them). Basic shapes (circle, rect, line, polyline) are converted to paths. Each `continuous_subpaths()` piece → one Stroke sampled at `max(8, ceil(length·samples_per_unit))` points; y negated. Closed subpaths keep their closing point (dropped later by `join_strokes`).

### `io/image.py`
`load_gray(path, max_dim:int) -> uint8 HxW` — Pillow, convert "L", downscale (LANCZOS) so max(H,W) ≤ max_dim.

### `io/export.py`
`to_json(spec_selected, n:int, mode) -> str` — keys sorted, floats via `repr(float(x))`, terms in selection order. NFR-1 is tested on this string.

### `render/`
- `frames.py` (pure): `frame_geometry(spec, n_frames) -> list[FrameGeom]` where `FrameGeom = {centers (m-1,), radii (m-1,), pen complex}`: `centers = chain[:-1]`, `radii = |c|` of terms 1..m−1 in selection order, `pen = chain[-1]`; `t_j = j/n_frames`.
- `animate.py` (I/O): matplotlib `FuncAnimation` over `frame_geometry`; draws circles (skip radius < 0.5 px on screen), radius segments, accumulated pen trail, optional faint original path. Writer: Pillow GIF; ffmpeg MP4 if available.
- `sweep.py`: grid of `evaluate` traces for a list of m.

### `cli.py`
```
python -m epicycles draw  SRC [--kind auto|svg|lineart|photo] [--samples auto|N] [--terms 256]
                              [--order magnitude|frequency] [--frames 600] [--fps 30]
                              [--threshold N] [--sigma 2.0 --low 0.1 --high 0.2]
                              [--min-component 20 --spur 5] [--max-dim 800]
                              [--json coeffs.json] [--out out.gif]
python -m epicycles sweep SRC --terms 1,4,16,64,256,1024 --out grid.png
python -m epicycles info  SRC        # N, stroke count, connector length, error table
```
`--kind auto`: `.svg` → svg; raster → lineart if Otsu ink fraction < 15 %, else photo.
`--samples auto`: 2048 for svg; next power of two ≥ tour point count, capped at 16384, for rasters.

## Dependencies
| package | why |
|---|---|
| numpy | FFT, arrays |
| svgpathtools | SVG path parsing/sampling |
| pillow | raster load, GIF writer |
| scikit-image | Otsu, Canny, skeletonize, labelling |
| matplotlib | animation |
| pytest, hypothesis (dev) | tests, property tests |

## Layout
```
pyproject.toml
src/epicycles/{__init__,__main__,cli}.py
src/epicycles/core/{path,fourier,tour,raster}.py
src/epicycles/io/{fetch,svg,image,export}.py
src/epicycles/render/{frames,animate,sweep}.py
tests/fixtures/{circle,square,two_strokes,lineart_cc0}.svg  # small, committed
tests/conftest.py          # hypothesis profile: derandomize=True, deadline=None
tests/test_<module>.py
```
