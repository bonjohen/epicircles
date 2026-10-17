# Plan — epicycles

Each unit: doc → RED → GREEN → refactor (see CLAUDE.md). Tests listed are the minimum; add more, never fewer.

## P0 — Scaffold
- [x] **U0 scaffold** — `pyproject.toml` (src layout, deps per design), package skeleton, `python -m epicycles --help` exits 0.
  Also `tests/conftest.py` registering and loading a hypothesis profile with `derandomize=True`.
  Tests: `test_cli_help_exits_zero`.

## P1 — Math core (synthetic data only)
- [x] **U1 spectrum** — `dft_ref`, `spectrum`.
  Tests: circle `a + r·e^{2πin/N}` → c_0 = a, only other term k=1 with |c|=r (**AC-1a**); clockwise circle → k=−1; constant → only k=0; `spectrum` ≈ `dft_ref` (hypothesis, random z, N∈[4,256]); canonical k order and range for even and odd N; translation by `a` changes only `c_0` by `a`.
- [x] **U2 evaluate/chain** — `evaluate`, `chain`.
  Tests: full spectrum reproduces samples at `t=n/N` (1e-9); `chain` length m, `chain[0]==c_0`, `chain[-1]==evaluate`; `chain` raises if k=0 is not first; ellipse from k=±1 traces correct semi-axes.
- [x] **U3 select/error** — `select`, `error`.
  Tests: magnitude ordering + documented tie-break; frequency ordering; k=0 first and counted in m; sampled == Parseval within rtol/atol (hypothesis); rms non-increasing in m (magnitude mode); m=N → rms < 1e-9·scale; percent uses max(width, height); zero-size bbox raises.
- [x] **U4 resample** — `arc_length`, `resample`.
  Tests: unit square perimeter 4; resample(square, 8) gives the 4 corners + 4 midpoints in order; spacing uniform within 1e-9; zero-length raises; first point preserved.
- [x] **U5 export** — `to_json`.
  Tests: schema keys; two runs → identical bytes; round-trip parse reconstructs same `evaluate` output.

## P2 — SVG line art from the web
- [x] **U6 fetch** — Tests (monkeypatched `urllib.request.urlopen`): download once, second call no network; cache name = sha256 prefix + ext; extension from Content-Type when URL has none; unknown Content-Type raises; local path passthrough; User-Agent sent.
- [x] **U7 load_svg** — fixtures `circle.svg` (a `<circle>` element), `square.svg`, `two_strokes.svg`, `transformed.svg` (path inside `<g transform="translate(10,20) scale(2)">`), `offset_viewbox.svg` (viewBox with nonzero min-y).
  Tests: circle → 1 stroke, points within 1e-6·r of radius; y negated (higher on screen → larger y); transform applied (matches hand-computed coordinates); offset viewBox handled; `two_strokes` → 2 strokes; sample count rule.
- [x] **U8 join_strokes** — Tests: single closed stroke → duplicate endpoint dropped, connector 0; single open segment → connector = its length (closing jump); two parallel segments joined with reversal, connector = join + closing jump, exact; deterministic on ties; output point count = sum of inputs minus dropped duplicates.
- [x] **U9 frames + animate** — Tests: `frame_geometry` count = n_frames; frame 0 pen == `evaluate(0)`; centers/radii length m−1; radii in selection order; `animate` writes a non-empty GIF with expected frame count (read back with Pillow, `n_frames`).
- [x] **U10 CLI draw/info (SVG)** — Tests: `draw tests/fixtures/circle.svg --terms 3` produces GIF + JSON; `info` prints error table; **AC-1b**; **AC-2** on `lineart_cc0.svg` (commit a small public-domain, stroke-based SVG; record source URL + licence in `tests/fixtures/SOURCES.md`).
  Manual (**AC-5**, SVG): run on a URL (e.g. a CC0 SVG from Wikimedia Commons or openclipart) and eyeball the GIF.
- [x] **U10b sweep** — `render/sweep.py` + `sweep` command. Tests: grid PNG written; panel count = len(terms); traces come from `evaluate` with the given m (assert on data handed to the plotter, not pixels).

## P3 — Raster line art
- [x] **U11 binarize/skeleton** — synthetic fixtures drawn in-test with `PIL.ImageDraw` (3-px-wide rectangle outline, a "T").
  Tests: Otsu picks ink on white bg; skeleton of 3-px rectangle is 1 px wide and stays within 1 px of the centreline.
- [x] **U12 skeleton_to_strokes** — Tests: every skeleton pixel appears in the walk; consecutive points 8-adjacent (|Δ| ≤ √2); walk closed (last adjacent to first); "T" (a tree of p pixels) → 2(p−1) points; deterministic start pixel; pixel-centre coordinate mapping; a 2000×2000 spiral skeleton completes without `RecursionError`.
- [x] **U13 multi-component + CLI lineart** — two disjoint shapes → 2 strokes → one tour, connector reported; `--kind auto` picks lineart; `--samples auto` picks next power of two ≥ tour length (capped 16384); **AC-3** (coverage + 95 % rule at M=2048).

## P4 — Photos via edge detection
- [x] **U14 edges** — Tests: filled disk image (uint8) → edge ring at radius ±1.5 px with default thresholds (proves the [0,1] conversion); higher sigma → fewer edge pixels on a noisy synthetic (seeded noise).
- [x] **U15 prune** — Tests: components below `min_component_px` removed; spur of length < `spur_len` removed from a line; main line untouched.
- [x] **U16 CLI photo** — `--kind photo` path wired with `--sigma/--low/--high/--min-component/--spur/--max-dim`; auto-detect test on synthetic photo-like image; **AC-4** manual on a real photo, **AC-5** (manual) for raster and photo URLs.

## P5 — Optional
- [x] **U17 two_opt** stroke-order improvement; test: connector length never increases, deterministic.
- [x] **U18 Euler stroke extraction** to reduce retracing; test: total length ≤ DFS walk.
- [x] **U19 browser renderer** — single HTML page that loads `coeffs.json` and animates on canvas with an M slider.

## P6 — labels, pen-up, smooth jumps, colour (FR-11…FR-15, AC-6…AC-8)
_Order (John decision, sync MSG 11): U20 first. Commit `tests/fixtures/me3.png` (crop of John's portrait, max-dim 800; SOURCES.md: "John Boen, own image, used with permission") as the AC-8 fixture before U20 GREEN._
- [ ] **U20 labels + pen-up + smooth jumps** — labelled tour `(z, seg_label)`, `PEN_UP=-1`; `join_labeled(strokes, labels)`; `resample_labeled(z, seg_label, n, jump_time)` smoothstep connectors; `error(..., mask)` masked; `segments` in JSON export; renderer skips pen-up runs (`frames.trail_labels` / NaN-break); `web/index.html` reads `segments`; CLI `--jump-time`.
  Tests: labels survive join/resample; no pen-down sample lies on a connector; smoothstep connector has near-zero velocity at both ends (finite-difference speed at each end < half the mid-segment speed); a pure discontinuity vs a smooth jump, both at the same `jump_time`, gives smooth masked error < discontinuity masked error at M=64; **AC-7** (M∈{64,256}); JSON `segments` round-trip; renderer runs equal label runs (data assertion, not pixels); **AC-8** on `me3`: (a) no pen-down sample on a connector, (b) masked error metric per John's ruling on the MSG 17 escalation (current-pipeline **masked** baseline) at M∈{1024,2048}.
  Manual (**AC-8c**): `demo/me3_before.gif` (current) and `demo/me3_after.gif` (pen-up, smooth jumps), same M/frames, each < 5 MB; post masked error for both to sync.
- [x] **U20b SVG colour** (FR-14) — `load_svg` returns `(strokes, colours)`; `stroke` attribute parsed (hex/`rgb()`/named, group-inherited). Tests: `stroke="#00f"` → that colour; group inheritance; `none`/missing → default ink. _(Split from U20 if it slows U20, per MSG 11.)_
- [x] **U21 regions** (FR-15, AC-6) — `core/regions.py`: `quantize`, `region_boundaries`; `--kind regions --palette P --boundaries both|foreground` (default `both`, two-tone). Tests: quantize deterministic; **AC-6**; a brown-ring hole has opposite orientation and still gets the ring colour; `both` vs `foreground` shared-edge counts; background detection; CLI.
  Manual: Apollo-17 Earth `--kind regions --palette 5` (default `both`) on a dark canvas → GIF in `demo/`, plus `--kind photo` for comparison; post both masked errors to sync.
