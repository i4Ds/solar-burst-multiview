# Are the sub-second peaks of the 04:28 burst real? (0.25 s, 148.5 MHz)

[claude], 13 Oct 2026. Script: `scripts/burst025s_significance.py`.
Output: `figures/flare20220930/burst025s_ch116_significance.{png,json}`.

Input: the P-AIRCARS cube of the first 0.25 s chunk,
`data/flare20220930/overnight/1348547272_025s_ch116_c2_burst.npz`
(224 frames, 04:28:15.8–04:29:11.6, coarse channel 116, beam 179″ × 90″).

## Measured

| quantity | value |
|---|---|
| off-Sun rms | scales with the burst peak: dynamic range 200–400 |
| statistical error of the box sum (rms, correlated over one beam) | 0.4 % per frame (median) |
| upper bound on per-frame noise, all frame-to-frame jitter counted as noise | box sum 3.0 %, peak 10.1 % of the main-burst median |
| lag-1 autocorrelation of the residual after a 2 s running median | 0.53 (lags 2–4: −0.09, −0.36, −0.47) |
| box-sum peaks with prominence > 5σ (upper-bound σ) | 13 (> 3σ: 19) |
| main-burst centroid (04:28:30–04:28:58, 109 frames) | (+302″, +123″) ± (10″, 10″) |

Peaks > 5σ: 04:28:21.80 (13σ), 24.30 (6σ), 31.80 (7σ), 38.80 (7σ),
**44.05 (40σ)**, 47.30 (8σ), 49.30 (8σ), 51.55 (12σ), 54.05 (7σ), 55.55 (6σ),
56.55 (16σ), 57.55 (6σ), 04:29:00.30 (17σ).

## What this says

- The peaks are far above the image noise and above the conservative bound.
- The residuals are correlated over two frames (≈ 0.5 s). Frame-independent
  calibration errors would give a lag-1 autocorrelation near zero. The negative
  values at lags 3–4 are at least partly made by the 2 s running-median detrending.
- Use the **box sum**, not the peak Jy/beam: the peak varies about 3× more
  (relative) than the box sum because the fitted source size changes from frame
  to frame. Some maxima of the peak light curve in the movie (04:28:30.55,
  35.55, 37.05) are not peaks of the box sum.
- All main-burst peaks are at the same position within the ±10″ scatter: one
  emission channel with repeated brightenings, not separate locations.
- Outside the main burst the centroid is further north (y ≈ 150–240″): the
  precursor at 04:28:21.80 is at (+267″, +233″), ≈ 120″ north of the main
  source, and the late peak at 04:29:00.30 at y ≈ 179″. A single Gaussian
  cannot tell a moving source from two fixed sources with a changing
  brightness ratio.

## Not established

- Whether P-AIRCARS self-calibration can change the amplitude scale frame by
  frame (not checked in its code or logs). Independent checks: a 0.25 s light
  curve from short baselines in the Birli MS (before self-cal), and e-Callisto
  near 148 MHz.
- Whether each peak is a separate electron beam: that needs the frequency drift
  of each peak, i.e. more coarse channels at 0.25 s (for example 101–131).
- "Jets": the sub-second peaks cannot be individual coronal (EUV) jets, which
  last minutes. Whether a coronal jet feeds the northern source is a question
  for AIA at the 04:28:21.8 position.
