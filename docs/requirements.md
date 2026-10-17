# Requirements — epicycles

## Goal
Reconstruct a 2-D drawing as the trace of a chain of rotating vectors (epicycles) whose radii, phases and speeds are the drawing's Fourier coefficients, and animate it. Built incrementally from clean vector line art to arbitrary photos via edge detection.

## Inputs (in delivery order)
| ID | Source | Example |
|---|---|---|
| IN-1 | SVG file or URL (paths and basic shapes; group transforms applied) | CC0 line art from Wikimedia Commons / openclipart |
| IN-2 | Raster line art (PNG/JPG, dark strokes on light background) | scanned or exported drawing |
| IN-3 | Arbitrary photo (PNG/JPG) | portrait, object photo |

Input guidance: prefer **stroke-based** line art. Filled-shape SVGs (e.g. potrace output, outlined fonts) describe the outline of each thick stroke, so they reconstruct as double contours. That is supported but expected, not a bug.

## Functional requirements
- **FR-1** The system MUST convert any supported input into one closed, ordered polyline (a "tour").
- **FR-2** The tour MUST be resampled to N points uniform in arc length. N is configurable (power of two not required). Default: 2048 for SVG; for raster inputs, the next power of two ≥ the tour's point count, capped at 16384.
- **FR-3** The system MUST compute complex Fourier coefficients `c_k`, `k ∈ [-⌊N/2⌋, ⌈N/2⌉-1]`, of the resampled tour.
- **FR-4** The system MUST reconstruct the path from the top-M coefficients (M configurable; M counts the k=0 term) using either ordering mode: `magnitude` (largest |c_k|, default) or `frequency` (smallest |k|).
- **FR-5** The system MUST report reconstruction error as RMS distance and as % of the drawing's larger bounding-box dimension, max(width, height), both from samples and from Parseval (dropped energy); the two MUST agree within rtol 1e-9, atol 1e-12·scale.
- **FR-6** The system MUST render an animation (GIF; MP4 if ffmpeg present) showing circles, radius vectors, and the pen trace.
- **FR-7** The system MUST support a sweep mode rendering a static grid of reconstructions for a list of M values (e.g. 1, 4, 16, 64, 256, 1024).
- **FR-8** The system MUST accept a URL for any input type, download it once, and cache by SHA-256 of the URL. If the URL has no file extension, it is taken from the response Content-Type.
- **FR-9** The system MUST export coefficients as JSON `{N, ordering, terms:[{k, re, im}]}` so other renderers (e.g. a browser canvas) can consume them.
- **FR-10** Multi-stroke inputs MUST be joined into one tour with connector segments; total connector length MUST be reported, including the closing jump back to the start unless the tour is already closed.
- **FR-11** (U20) Every tour sample MUST carry a label: a colour index ≥ 0, or `PEN_UP = -1`. Renderers MUST NOT draw pen-up spans. Labels are tied to the parameter t, not to position: the colour at time t is the label of sample ⌊t·N⌋.
- **FR-12** (U20) Connector segments MUST be pen-up and MUST be traversed with a smooth speed profile (zero velocity at both ends) in a fixed parameter-time slot `jump_time` (fraction of the period per jump; CLI `--jump-time`, default `2/M` clamped to [0.002, 0.05]). Visible strokes keep constant speed and share the remaining time in proportion to their length.
- **FR-13** (U20) Reported error MUST be computed over pen-down samples only ("masked error"). Parseval no longer applies to it, so masked error comes from the samples directly. The unmasked Parseval check stays as an internal consistency test.
- **FR-14** (U20b) SVG strokes MUST take their colour from the `stroke` attribute (style or attribute, inherited through groups; `none`/missing → default ink).
- **FR-15** (U21) A new input kind `regions` MUST quantize the image to a palette of P colours (default 6, `--palette P`) and trace the boundary of each colour region, colouring each boundary by its interior region. For shared boundaries, `--boundaries both|foreground` (default **`both`**, per John decision 2026-10-16): `both` draws each shared edge twice side by side, each pass in the colour of the region on its left; `foreground` draws each shared edge once in the colour of the smaller-area region, excluding the background colour (the palette entry with the largest border-pixel count).

## Non-functional
- **NFR-1** Deterministic: identical input + options + environment (same numpy build) → identical coefficient JSON bytes. Across numpy builds, FFT results may differ in the last bit, so only numeric equality to 1e-12 is promised.
- **NFR-2** N=8192 DFT + reconstruction under 1 s on a laptop (uses `numpy.fft`; a reference O(N²) DFT exists for tests only).
- **NFR-3** No network access in tests. Test suite under 30 s.
- **NFR-4** Minimal dependencies (see design).

## Acceptance
- **AC-1** (a) Synthetic circle of radius r centred at any point a: c_0 = a, a single other coefficient with |c_k| > 1e-9·r, at k=±1, |c| = r. (b) Circle SVG through the full pipeline: excluding k=0, the k=±1 term has |c| within 1e-3·r of r and every other term is below 1e-3·r.
- **AC-2** A public-domain stroke-based SVG line drawing reconstructs at M=512 with error < 0.5 % of its larger dimension.
- **AC-3** A raster line-art PNG, reconstructed at M=2048: every skeleton pixel lies within 2 px of the reconstruction (coverage), and ≥ 95 % of reconstruction samples lie within 2 px of a skeleton pixel (the rest are connectors).
- **AC-4** A photo produces a recognizable animation; edge-filter parameters are exposed on the CLI.
- **AC-5** (manual, since tests are offline) `python -m epicycles draw <url> --terms 256 --out out.gif` works end-to-end for each input type. The automated equivalent runs on local fixtures.
- **AC-6** (U21) On a synthetic image (blue disk on a brown square on white): with `--boundaries foreground`, `regions` yields exactly two coloured loops, disk→blue and square outline→brown; with the default `both`, it yields three (the disk edge also appears as the brown square's hole, in brown). In both modes no pen-down sample lies within 1 px of a connector.
- **AC-7** (U20) For a two-stroke drawing, masked error with smooth jumps at `jump_time=2/M` is ≤ masked error with zero-time jumps, and ≤ the unmasked arc-length baseline, at M ∈ {64, 256}.
- **AC-8** (U20, on `me3`) (a) no pen-down sample lies on a connector; (b) at M ∈ {1024, 2048}, masked error with smooth jumps is lower than the current (unmasked) pipeline's error; (c) manual: `demo/me3_before.gif` (current behaviour) and `demo/me3_after.gif` (pen-up, smooth jumps), same M and frames, each under 5 MB, with masked error for both posted to sync.

## Out of scope (v1)
Real-time GUI, freehand drawing input, 3-D, GPU.
