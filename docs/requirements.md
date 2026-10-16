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

## Out of scope (v1)
Real-time GUI, freehand drawing input, colour, 3-D, GPU.
