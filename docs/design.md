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
- `Tour`: the closed path. Up to U19 this is a bare `np.ndarray[complex128]`, shape `(n,)`, closed (last point connects to first; first point is **not** repeated at the end). **From U20** a Tour is a pair `(z: complex128 (n,), label: int16 (n,))`: same geometry in `z`, plus a per-sample label — a colour index ≥ 0, or `PEN_UP = -1` for connector samples renderers must not draw. See §P6.
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
| `select` | `(spec, m:int, mode:"magnitude"\|"frequency") -> Spectrum` | m terms including k=0. k=0 always first (for m≥1); the remaining m−1 by mode. magnitude: sort by (−\|c\|, \|k\|, k). frequency: sort by (\|k\|, k). Returned in selection order — the drawing order of the chain. Missing k=0 term → `ValueError`; `m<1` → returns just the k=0 term |
| `evaluate` | `(spec, t: np.ndarray[float]) -> np.ndarray[complex]` | `Σ c e^{2πikt}` for each t |
| `chain` | `(spec, t: float) -> np.ndarray[complex] (m,)` | partial sums in selection order. `chain[0] = c_0` (anchor), `chain[j]` = centre of circle j+1, `chain[-1] == evaluate(spec,[t])[0]` (pen). Raises `ValueError` unless k=0 is at index 0 (i.e. a `select` result) |
| `error` | `(z, full:Spectrum, kept:Spectrum) -> ErrorReport` | dataclass `{rms_sampled, rms_parseval, pct_height}` |

### `core/tour.py`
| fn | signature | contract |
|---|---|---|
| `join_strokes` | `(strokes: list[Stroke]) -> (Tour, connector_len: float)` | greedy: start with stroke 0; repeatedly append the unused stroke whose either endpoint is nearest the current end (reversing if needed); ties → lowest index, then forward orientation. Concatenate points; closing segment implied. connector_len = sum of joins + the closing jump (last point → first point). A stroke whose last point equals its first (within 1e-9·scale) has that duplicate dropped and contributes 0 closing length |
| `two_opt` (P5) | `(strokes, order) -> order` | optional stroke-order improvement. `order` is a list of `(index, reversed)` pairs over `strokes`; a 2-opt pass reverses cyclic sub-segments (flipping their orientation), accepting only strictly-improving moves, so the connector length never increases and the result is deterministic |
| `order_connector_length` (P5) | `(strokes, order) -> float` | cyclic connector length of an `(index, reversed)` ordering: `Σ |end(order[i]) − start(order[i+1])|` including the closing jump. The metric `two_opt` minimises |

### `core/raster.py`
| fn | signature | contract |
|---|---|---|
| `binarize` | `(gray: uint8 HxW, threshold:int\|None) -> bool HxW` | True = ink = `gray <= threshold`. None → Otsu. skimage's Otsu splits foreground as `> threshold`, so ink (dark) is the `<=` side; this also handles a purely bimodal image, where Otsu returns the low class value. A **uniform** image (`min==max`) has no foreground to separate, so None-threshold returns an all-`False` (no-ink) mask instead of Otsu's degenerate "all ink" |
| `edges` | `(gray, sigma, low, high) -> bool HxW` | converts to float in [0,1] (`skimage.util.img_as_float`), then `skimage.feature.canny(sigma, low_threshold=low, high_threshold=high)`. Thresholds are absolute gradient values on that [0,1] scale |
| `skeleton` | `(mask) -> bool HxW` | `skimage.morphology.skeletonize` |
| `prune` | `(skel, min_component_px:int, spur_len:int) -> bool HxW` | drop small 8-connected components; remove end-branches shorter than spur_len |
| `skeleton_to_strokes` | `(skel) -> list[Stroke]` | one stroke per 8-connected component: DFS closed walk over the pixel graph (each tree edge traversed out and back), **iterative with an explicit stack**, start = lowest (row, col) pixel, neighbour order fixed (N, NE, E, SE, S, SW, W, NW). Visits every pixel; consecutive points 8-adjacent; the final return to the start is not repeated. A tree of p pixels yields 2(p−1) points. Pixel centre → `x=col+0.5`, `y=H-row-0.5` |
| `skeleton_to_strokes_euler` | `(skel) -> list[Stroke]` | like `skeleton_to_strokes`, but each 8-connected component whose pixel graph is **Eulerian** (every vertex even degree) is traversed by a **Hierholzer** Euler circuit — each edge exactly once, no out-and-back doubling. Components with any odd-degree vertex fall back to the DFS walk. Total walk length ≤ the pure DFS walk. Deterministic: components ordered by lowest (row, col), per-node adjacency sorted, Hierholzer starts at the lowest pixel. Same coordinate map and closing-point rule as `skeleton_to_strokes` |

DFS retrace doubles path length but always yields a valid closed walk; that is the v1 choice. The cost: the DFS tree drops loop edges, so a closed loop (e.g. a rectangle outline) is also traversed out and back, drawing it twice. Euler-path extraction with minimal duplication (U18) addresses this *where a component is Eulerian*.

**Library-only in v1 (F5.3, John decision 2026-10-16).** `skeleton_to_strokes_euler` and `two_opt` are implemented and tested but **not wired into any CLI or pipeline path** — the `draw`/`info`/`sweep` commands always use `skeleton_to_strokes` (DFS) and the greedy `join_strokes`. CLI output therefore still contains the DFS out-and-back doubling and greedy connector ordering; U18's de-doubling and 2-opt's shorter tours are available to library callers only, with no CLI flags in v1.

**8-connected parity (U18 finding).** On an 8-connected skeleton a corner is three mutually-adjacent pixels (an L plus its diagonal short-cut), so the corner pixel has **degree 3**. Most real skeleton loops therefore contain odd-degree vertices and are **not** Eulerian — `skeleton_to_strokes_euler` falls back to DFS on them, and only avoids doubling on clean even-degree loops (e.g. a 4-connected diamond, which is why the U18 test fixture is a 45° diamond, not a square). Dropping diagonal short-cut edges before the parity check (prefer 4-adjacency) would enable Euler on more loops — deferred (F5.5).

### `io/fetch.py`
`fetch(src: str, cache_dir: Path) -> Path` — local path passthrough; URL → `cache_dir/sha256(url)[:16] + ext`, downloaded via `urllib.request` once, with a User-Agent header (Wikimedia rejects requests without one). `ext` from the URL path; if absent, from Content-Type (`image/svg+xml`→`.svg`, `image/png`→`.png`, `image/jpeg`→`.jpg`; anything else raises). No retries.

### `io/svg.py`
`load_svg(path, samples_per_unit: float) -> list[Stroke]` — `svgpathtools.Document(path).paths()` (svgpathtools ≥ 1.8; this method replaced `flatten_all_paths`) so group and element `transform`s are applied to the returned path geometry (plain `svg2paths` ignores them, and most web clipart uses them). Basic shapes (circle, rect, line, polyline) are converted to paths. Each `continuous_subpaths()` piece → one Stroke. Sampling is **scale-invariant**: the total point budget `samples` is split across subpaths in proportion to their arc length, `n_i = max(8, round(samples · len_i / Σlen))`. (An absolute per-unit density would collapse small-viewBox icons — e.g. `0 0 24 24` — to 8-point polygons, losing the curves before the DFT.) Points are taken at `linspace(0,1,n_i)`; y negated. Closed subpaths keep their closing point (dropped later by `join_strokes`).

### `io/image.py`
`load_gray(path, max_dim:int) -> uint8 HxW` — Pillow. Images carrying alpha (`RGBA`/`LA`/palette-with-transparency) are **composited over white** before the "L" conversion, so transparent regions read as background rather than as undefined RGB. Special case: if that composite is **uniform** while the alpha channel is **not** (e.g. a white glyph on a transparent field — flattening over white would make it all-white and misdetect as a blank photo), the alpha channel is used as ink instead: `gray = 255 − alpha`. Then downscale (LANCZOS) so max(H,W) ≤ max_dim.

The lineart and photo pipelines raise a clear `ValueError("no ink found in image")` when edge/skeleton extraction yields **no strokes**, checked before `resample` (otherwise the failure surfaces as the lower-level "cannot resample a zero-length tour").

### `io/export.py`
`to_json(spec_selected, n:int, mode) -> str` — keys sorted, floats via `repr(float(x))`, terms in selection order. NFR-1 is tested on this string.

### `render/`
- `frames.py` (pure): `frame_geometry(spec, n_frames) -> list[FrameGeom]` where `FrameGeom = {centers (m-1,), radii (m-1,), pen complex}`: `centers = chain[:-1]`, `radii = |c|` of terms 1..m−1 in selection order, `pen = chain[-1]`; `t_j = j/n_frames`. `trail_resolution(n_terms, n_samples=0) -> int = max(8·n_terms, n_samples, 2)` and `pen_path(spec, resolution) -> complex[(resolution,)] = evaluate(spec, arange(R)/R)` give the **dense** pen trajectory.
- `animate.py` (I/O): matplotlib `FuncAnimation` over `frame_geometry`; draws circles (skip radius < 0.5 px on screen), radius segments, the pen trail, optional faint original path. **The pen trail is sampled densely, not per frame**: it is `pen_path(spec, R)` with `R = trail_resolution(m, N)` (`N` = len(original) or 0), independent of `n_frames`, and revealed up to `round((i+1)/n_frames · R)` points on frame `i`. Frames set only the *timing*; the curve's resolution comes from `R`, so a high-term curve is smooth even at few frames (previously the trail was one point per frame, drawing an `n_frames`-gon). Writer: Pillow GIF; ffmpeg MP4 if available.
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

## Web renderer (`web/`)
A static page (`web/index.html`, no build step) that animates a coefficient file
on a `<canvas>`. Serve the folder over HTTP so `fetch` can read the JSON
(`python -m http.server`). Consumer contracts:

- **`coeffs.json`** — the FR-9 export, schema unchanged: `{N:int, ordering:str, terms:[{k,re,im}]}` (see `io/export.py`). The M slider ranges `1…terms.length`.
- **`original.json`** (optional sidecar) — places an optional source-image backdrop in the **same drawing coordinates** as the reconstruction: `{x, y, w, h}` where `(x, y)` is the image's **top-left corner in y-up drawing coords** and `w, h` are its width/height in drawing units. The page maps the backdrop by `toPx(x, y)` + `w·scale × h·scale`, so it registers with the trace rather than being fit to the trace bbox. Absent → the backdrop falls back to the trace bounding box.
- **`original.(png|jpg|svg)`** (optional) — the backdrop image, probed in that order; first that loads is used, drawn at 0.1 alpha under the animation. For a raster source this is the photo; for a vector source it is the drawing rasterized to its stroke bbox (see `web/SOURCES.md`). Missing → no backdrop.
- **UI toggles:** `circles` (epicycle circles), `target image` (the full-term reconstruction drawn as a faint reference underlay — *not* the literal source, just a dense reconstruction), `original (10%)` (the backdrop image above).

These demo assets are reproducible from `web/SOURCES.md`; they are a convenience renderer, not part of the Python package's tested surface (only the `coeffs.json` schema is covered by `test_browser.py`).

## P6 — labels, pen-up, smooth jumps (U20); SVG colour (U20b); regions (U21)

Introduces a per-sample **label** so connector segments are *pen-up* (traversed but not drawn), which removes the straight "lines between sections" in multi-stroke output.

**Types.** A labelled `Tour` is `(z: complex128 (n,), label: int16 (n,))`. `PEN_UP = -1`; `Palette = uint8 (P,3)` (U21). Label ≥ 0 is a colour index (default ink = 0 when there is no colour source); `PEN_UP` marks connector samples renderers MUST NOT draw. The colour at parameter t is `label[⌊t·N⌋]` (FR-11).

**`join_strokes(strokes, labels=None) -> (Tour, connector_len)`** (U20). Same greedy ordering, now label-carrying: each stroke's pen-down points take its label (0 if `labels` is None); the connector points between strokes and the closing jump carry `PEN_UP`. Geometry and `connector_len` are unchanged from the v1 row above. Connector points are just the two bridged endpoints; their *timing* is assigned in `resample`.

**`resample(tour, n, jump_time=0.0) -> Tour`** (U20). Labelled, non-uniform-in-time resample. The period splits into parameter-time slots: each connector gets a fixed `jump_time` fraction (FR-12); the remaining time divides among pen-down segments in proportion to arc length (constant pen speed within each visible stroke). On a connector `a→b`, position `= a + (b−a)·s(u)`, `u ∈ [0,1]`, smoothstep `s(u) = 3u² − 2u³` (zero velocity at both ends). Pen-down samples copy their segment's label; connector samples are `PEN_UP`. **`jump_time=0.0` reduces to the v1 arc-length resample** (connectors collapse to zero time, no pen-up slot), so existing callers are unaffected. Deterministic; raises `ValueError` on zero total pen-down length.

**`error(z, full, kept, mask=None) -> ErrorReport`** (U20). With `mask` (`label != PEN_UP`), `rms_sampled` and `pct_height` are computed over **pen-down samples only** (FR-13); `rms_parseval` stays the unmasked Parseval value, retained only as an internal consistency check (it no longer equals the masked rms). `mask=None` → v1 behaviour unchanged.

**`io/export.py`** (U20). JSON gains `"segments": [{"t0","t1","colour":[r,g,b]}]` for pen-down spans only (one per visible-stroke run, in drawing order) plus `"background":[r,g,b]`. The `{N, ordering, terms}` keys are unchanged, so old consumers still work.

**`render/`** (U20). With the F7.1 dense trail, split the trail into runs by label, draw each run in its colour, and **skip `PEN_UP` runs**. Circles and radius arms stay neutral grey. Default canvas: dark (`#111`) for `photo`/`regions`, white for `svg`/`lineart`; `--canvas` overrides. New CLI flag `--jump-time` (default `2/M` clamped to [0.002, 0.05]).

**`web/index.html`** (U20). Read `segments`; colour the trail per span and skip pen-up gaps; fall back to single-colour when `segments` is absent.

**SVG colour (U20b, FR-14).** `io/svg.py` returns `(strokes, colours)`; colour from the `stroke` attribute (style or attribute, group-inherited): `#rgb`, `#rrggbb`, `rgb()`, or a CSS named colour from a small built-in table; anything else → default ink.

**`core/regions.py` (U21, FR-15)** — detailed contract added when U21 starts. `quantize(rgb, p) -> (index, Palette)` via Pillow `Image.quantize(colors=p, method=MEDIANCUT, dither=NONE)` (deterministic, no k-means). `region_boundaries(index, palette, mode) -> list[(Stroke, colour_idx)]` via `skimage.measure.find_contours(mask, 0.5)`, each contour oriented region-on-the-left by signed shoelace area (holes reverse, correctly); drop contours shorter than `min_component`. Default `both` draws each shared edge twice side-by-side (John decision 2026-10-16); `foreground` draws it once in the smaller region's colour, excluding background. Background = palette index with the most border pixels.

## Dependencies
| package | why |
|---|---|
| numpy | FFT, arrays |
| svgpathtools | SVG path parsing/sampling |
| pillow | raster load, GIF writer |
| scikit-image | Otsu, Canny, skeletonize, labelling |
| matplotlib | animation |
| pytest, hypothesis, scipy (dev) | tests, property tests; `scipy.spatial.cKDTree` in `test_lineart.py` (declared explicitly — it otherwise arrives only transitively via scikit-image) |

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
