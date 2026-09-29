# Plan: reproduce Sharma et al. 2022

Status: **29 September 2026.** Phases 0–1 are done. Phase 2 is in progress.
`python -m solarburst.figures` rebuilds paper Figures 3, 5, 7, 9, 11 and 12.
Figure 3 peaks match the caption to 15%. Figures 7–12 use a 6σ MAD detector on
the `Tb_*_sub.p` cubes; they match the paper's layout and IDs, not Table 2
counts pixel-for-pixel.

This document is only the Sharma reproduction. Standing up birli, hyperdrive,
and WSClean, including any later solar scan used to test that stack, is the
imaging-pipeline setup in [`calculon-mwa.md`](calculon-mwa.md). The 2024
campaign is item 7 of the sabbatical work plan, not a phase of this
reproduction.

Goal: regenerate the solar maps of Sharma et al. 2022 (ApJ 937, 99) from his
own products, and find out whether we understand the method.

---

## 1. Where the paper's data is

Checked on calculon, 2026-08-07.

The shared archive `/mnt/nas05/data02/MWA_data/data/mwa_data` does not contain
the 2015-12-03 obsids. It jumps from 2015-09-21 to 2022-03-01, and what it
holds is ASVO conversion output, not raw gpubox files. No ASVO account is
needed for this reproduction.

The paper's working tree is `/mnt/nas05/data02/rohit/`, world-readable:

| path | contents |
|---|---|
| `20151203_MWA/` (6.7 TB) | the main tree, containing everything in the next four rows |
| `20151203_MWA/new_ms/` | calibrated measurement sets, all nine bands, plus `cal_soln/` derived from calibrator 1133139776 |
| `20151203_MWA/new_ms/fits/` | 35,948 finished CASA images |
| `20151203_MWA/new_ms/fits_residual/` | 32,454 residual images |
| `20151203_MWA/Tb_new/` (47 GB) | brightness-temperature pickles per band, each with a `_sub` counterpart, plus residuals |
| `20151203_MWA/new_vis/` (2.0 TB) | per-baseline dynamic spectra |
| `20151203_sub/` (396 GB) | the visibility-subtraction workspace, almost entirely the 161 MHz band |
| `20151203_selfcal/` (159 GB) | self-calibration products at 161 and 240 MHz |
| `20151203_forward/` | PSIMAS/FORWARD `.sav` at ten frequencies, 100–240 MHz |
| `20151203_EUV/`, `20151203_LASCO/` | AIA 193 Å level-1 and coronagraph context |

The whole 2015-12-03 analysis is about 7.3 TB. It stays on calculon. We stage
slices. Paths, obsids, bands, and image geometry are pinned in
`configs/sharma2022.yaml`.

The published images are 1024², 50″ pixels, RA/Dec SIN projection, Jy/beam,
Stokes I, 0.5 s cadence, 4.2 MB each — 6 obsids × 9 bands × 570 timesteps.
A seventh scan, 1133149192, was processed separately and is partial.

Inside `20151203_sub/161MHz` the subtraction step survives as a matched pair:

| file | size | role |
|---|---|---|
| `1133148288_125-126_chan.ms` | 642 MB | input to the subtraction |
| `1133148288_125-126_chan_sub.ms` | 577 MB | Sharma's subtracted output |
| `1133148288_125-126.ms` | 34 GB | full-resolution calibrated MS |

1.2 GB gives a direct test of the core algorithm on the laptop.

---

## 2. Where the reproduction runs

**Laptop** — Phases 1 and 2. Read measurement sets with `python-casacore`,
subtract, detect sources, convert Jy/beam to brightness temperature, reproject,
and write the figures. No radio-astronomy binaries.

**Calculon GPU nodes** — Phase 3, re-imaging calibrated visibilities. The
containers and the Slurm invocation are in [`calculon-mwa.md`](calculon-mwa.md).
The login node cannot run them.

---

## 3. Phased plan

Each phase ends at a gate that is checkable against Sharma's own products.

### Phase 0 — Foundations — **done**

conda env from `environment.yml` (`python-casacore`, `reproject`, `scipy`,
`pyyaml`, `tqdm`). Package `src/solarburst/`, installed editable.
`configs/sharma2022.yaml` pins obsids, bands, calibrator, image geometry, and
calculon paths. `solarburst.stage` rsyncs named slices into `data/sharma2022/`.

**Gate, passed:** validation MS pair opens with `python-casacore`.

### Phase 1 — Validate the visibility subtraction — **done**

Read `1133148288_125-126_chan.ms` and diff against
`1133148288_125-126_chan_sub.ms`. The paper's §4.1 describes a 15 s running
median. The CASA logs (`casa-20200523-045753.log`) show `subvs` with
`mode="linear"` over the whole scan, including flagged samples. `scan_mean`
matches the MS bit-exactly (`|Δ| = 0` on 4.8 M visibilities).
`--method running_median` is the published algorithm, not this ground truth.

**Gate, passed:** subtracted visibilities agree with Sharma's to numerical
precision.

### Phase 2 — Rebuild the figures from the existing images — **in progress**

The map pipeline is in `src/solarburst/` (`maps`, `bursts`, `figures`). Figure
IDs are in the config `figures:` block. The time-average uses the **median**
of Sharma's Tb pickles (a mean is wrecked by a few hundred-MK frames at 197
and 240 MHz). 161 MHz and partial obsid `1133149192` are omitted, as in the
paper.

Pinned:

| Fig | What | IDs |
|---|---|---|
| 3 | Time-averaged total T_B, 8 bands, 0–0.40 MK, limb 16′ | median of `Tb_new/Tb_*.p` over the six `imaged: true` scans; no 161 MHz |
| 5 | Residual overlay, 108/179/240 MHz, contours 2×10⁴ K | pickle frame 0 = `1133148288_*.0008`, 03:24:36.5–37.0 UT |
| 7 | Burst-count maps + 1σ temporal variation | 6σ detection on residual cubes |
| 9 | AIA 193 + 240 MHz, six regions | `20151203_EUV/` |
| 11 | Time-averaged residual T_B after dropping 6σ timestamps | residual FITS / `_sub` pickles |
| 12 | Time-average of 6σ bursts + AIA overlay | same |

Two conversion facts that are not in the paper:

- Sharma's `_sub.ms` is a scan-mean, not the 15 s running median (Phase 1).
- Rayleigh–Jeans with the FITS `BMAJ`/`BMIN` is a factor ~9.5 below the pickled
  T_B (and the Figure 3 caption peaks). `imaging.tb_scale: 9.48` recovers the
  published scale; the pickles already include it. DATE-OBS on every snapshot
  FITS is the scan start, so frame time comes from the filename index / pickle.

**Gate, partly met:** Figure 3 peaks from the time median sit within ~15% of the
caption (0.26…0.47 MK). Figures 7–12 match layout and IDs; Table 2 region counts
are still approximate.

Phases 1 and 2 are independent, both laptop-native, and together are the whole of
"do we understand this paper".

### Phase 3 — Re-derive the images from the calibrated visibilities

Take the calibrated MS from `new_ms/<band>/`, apply our own subtraction, image
it with the calculon containers, and compare against `new_ms/fits`.

**Gate:** per-pixel agreement with `new_ms/fits` for a chosen obsid and band.

### Phase 4 — From raw visibilities (optional)

Only if Phases 1–3 leave the calibration itself in doubt. This is the one step
that would need an ASVO account, since the 2015-12-03 raw data is not held
locally. The existing `cal_soln/` solutions make it likely we can skip this.

---

## 4. Volumes and transfers

| what | size | where it runs |
|---|---|---|
| subtraction validation pair | 1.2 GB | laptop |
| one obsid × one band of FITS | 2.4 GB | laptop |
| all FITS images | ~150 GB | leave on calculon |
| one full-resolution calibrated MS | 34 GB | calculon |
| `Tb_new` pickles | 47 GB | selective |
| `new_vis` dynamic spectra | 2.0 TB | leave on calculon |
| entire 2015-12-03 analysis | 7.3 TB | leave on calculon |

The 2 TB laptop is comfortable as long as we stage selectively and never mirror
`new_vis` or the whole FITS set.

---

## 5. Open questions

- **Rohit's directory is a personal working tree.** Files date from 2019–2022
  with no guarantee of internal consistency, and some subdirectories are
  world-writable. Treat it as strictly read-only and stage copies. Figure 7–12
  region centres and Table 2 counts are still approximate without his mapping.
- **Scope of "reproduce".** Phases 1 and 2 answer the validation question at low
  cost. Phase 3 is the more rigorous claim and considerably more work. Whether
  Phase 3 has to pass before any later campaign is a question for the
  sabbatical work plan, not a phase of this document.
