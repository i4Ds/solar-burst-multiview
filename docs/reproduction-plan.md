# Plan: reproduce Sharma et al. 2022, then generalise

Status: **draft for review**. Nothing here is implemented yet; building starts on
the new laptop.

Goal, in two steps:

1. Reproduce the solar maps of Sharma et al. 2022 (ApJ 937, 99) as a validation
   exercise — do we understand the method well enough to regenerate its outputs?
2. Turn the visibility-subtraction imaging method into a reusable, config-driven
   tool and point it at the 2024 MWA solar observations. No STIX.

---

## 1. Where we actually stand

A survey of calculon on 2026-08-07 changed two working assumptions.

### The paper's data is not in the shared archive

`/mnt/nas05/data02/MWA_data/data/mwa_data` is 16 TB over 2546 distinct obsids,
but it jumps from 2015-09-21 straight to 2022-03-01. The 2015-12-03 obsids are
absent. That archive is also not raw gpubox data — it is ASVO *conversion*
output, `<obsid>_<jobid>_ms.tar` at roughly 6–9 GB each, plus small
`<obsid>_<jobid>_vis_meta.tar` metadata tarballs. 347 obsids fall in calendar
2024, so the birli preprocessing stage is already done for the eventual target
data.

### The paper's full working tree is in Rohit Sharma's directory

`/mnt/nas05/data02/rohit/` is world-readable and holds the original analysis:

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

The whole 2015-12-03 analysis is about 7.3 TB, so it stays where it is; we stage
slices from it rather than mirroring any of it.

The published images are 1024², 50″ pixels, RA/Dec SIN projection, Jy/beam,
Stokes I, 0.5 s cadence, 4.2 MB each — exactly 6 obsids × 9 bands × 570
timesteps. A seventh scan, 1133149192, was processed separately and is partial.

The consequences are large: **no ASVO account is needed for the reproduction**,
and we have ground truth at every intermediate stage rather than only at the
published figures. Everything is pinned in `configs/sharma2022.yaml`.

### The one asset that matters most

Inside `20151203_sub/161MHz` the subtraction step survives as a matched pair:

| file | size | role |
|---|---|---|
| `1133148288_125-126_chan.ms` | 642 MB | input to the subtraction |
| `1133148288_125-126_chan_sub.ms` | 577 MB | Sharma's subtracted output |
| `1133148288_125-126.ms` | 34 GB | full-resolution calibrated MS |

1.2 GB gives a direct unit test of the core algorithm, runnable entirely on the
laptop.

### Software gaps

The calculon login node is bare Ubuntu with system Python 3.12 and gcc. No
conda, cmake, Docker, Apptainer, Singularity, CASA, WSClean, hyperdrive, birli
or giant-squid. Storage is not a constraint: 272 TB free on `/data`, 113 TB on
`/scratch`.

---

## 2. Where each piece of work runs

**New MacBook (M5 Pro, 2 TB, 64 GB)** — everything Python-only: reading
measurement sets through `python-casacore`, the subtraction itself, source
detection, Jy/beam → brightness-temperature conversion, helioprojective
reprojection, and all figures. `python-casacore` 3.8.1 is on conda-forge for
osx-arm64, so this needs no compilation. This is where Phases 1 and 2 live
end to end.

**Calculon** — anything needing WSClean, hyperdrive, birli or CASA proper:
re-imaging from visibilities, recalibration, and bulk processing of the 2024
archive. Requires a software stack that does not exist yet.

**CSCS** — full-scale deployment later, once the pipeline is proven and
containerised. Calculon is the staging rehearsal for it.

---

## 3. Phased plan

Each phase ends at a gate that is checkable against Sharma's own products, so we
find out quickly if our understanding is wrong.

### Phase 0 — Foundations (new laptop, ~half a day)

- conda env from `environment.yml`, adding `python-casacore`, `reproject`,
  `scipy`, `pyyaml`, `tqdm`.
- Package skeleton `src/solarburst/`, installed editable, replacing the
  notebooks-first layout for anything reusable. Notebooks become thin drivers.
- `configs/sharma2022.yaml` — already drafted, contains the obsids, band/coarse-
  channel mapping, calibrator, image geometry, and every calculon path.
- A staging module that rsyncs named slices from calculon into `data/sharma2022/`,
  so no path is ever hardcoded in a notebook.

**Gate:** `rsync` the 1.2 GB validation pair and open both with `python-casacore`.

### Phase 1 — Validate the visibility subtraction

The scientific crux, and cheap. Read `1133148288_125-126_chan.ms`, implement the
running-median background subtraction, and diff the result against
`1133148288_125-126_chan_sub.ms`.

The paper's §2 gives the method but we should expect to recover some parameters
empirically: the median window length, whether it acts on complex visibilities or
amplitudes, whether it is per-baseline/channel/polarisation, and how flagged data
is handled. The ground-truth pair makes this a search over a small parameter
space with an unambiguous success criterion instead of guesswork.

**Gate:** our subtracted visibilities agree with Sharma's to numerical precision.
Reaching this means the core method is genuinely understood — the single most
important checkpoint in the whole plan.

### Phase 2 — Rebuild the figures from the existing images

Stage a targeted subset of `new_ms/fits` (one obsid × one band × 570 timesteps is
2.4 GB; the full set is ~150 GB, which we do not want). Then build the map
pipeline: Jy/beam → brightness temperature using the beam in the header,
RA/Dec → helioprojective via `sunpy`/`reproject`, solar limb overlay, and the
paper's colour scales.

First task here is a careful pass through the PDF to pin down which obsid, band
and timestep back each of Figures 3, 5, 7, 9, 11 and 12 — 570 timesteps per band
is far too many to search blindly. Those get recorded in the config as a
`figures:` block.

**Gate:** side-by-side visual match with the published figures, plus agreement in
peak brightness temperature and source position.

Phases 1 and 2 are independent, both laptop-native, and together are the whole of
"do we understand this paper".

### Phase 3 — Re-derive the images from the calibrated visibilities

This is where reproduction becomes more than re-plotting. Take the calibrated MS
from `new_ms/<band>/`, apply our own subtraction, image it, and compare against
`new_ms/fits`.

Needs an imaging stack on calculon. Two options, in preference order:

1. Ask FHNW IT for Apptainer, then run the standard MWA containers. Cleanest, and
   it is the same artefact we would later ship to CSCS.
2. Failing that, micromamba in user space gets CASA and `python-casacore`
   straightforwardly; WSClean and hyperdrive would need building from source
   against casacore, which is a real but bounded piece of work.

**Gate:** per-pixel agreement with `new_ms/fits` for a chosen obsid and band.

### Phase 4 — From raw visibilities (optional)

Only if Phases 1–3 leave the calibration itself in doubt. This is the one step
that *would* need an ASVO account, since the 2015-12-03 raw data is not held
locally. The existing `cal_soln/` solutions make it likely we can skip this.

### Phase 5 — Generalise to the 2024 observations

The payoff. Turn the validated pipeline on the 347 obsids of 2024 solar data
already sitting converted in the shared archive.

- A second config, `configs/mwa2024.yaml`, with no code changes required — that
  constraint is the real test of whether the tool generalised.
- Inspect one `_ms.tar` first to learn what time and frequency averaging ASVO
  applied, which sets what the subtraction can resolve.
- Handle the legacy vs MWAX correlator difference; 2024 data is MWAX, 2015 is
  legacy, and they differ in channelisation and metadata conventions.
- Calibration strategy for the 2024 epoch: identify bracketing calibrator scans
  and decide whether self-calibration on the Sun is needed.
- Then burst detection and the science.

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
| one 2024 obsid, converted | 6–9 GB | calculon |

The 2 TB laptop is comfortable as long as we stage selectively and never mirror
`new_vis` or the whole FITS set.

---

## 5. Open questions and risks

- **Apptainer on calculon.** Worth asking IT early, since it gates Phase 3 and is
  also the path to CSCS. Everything before Phase 3 is unblocked regardless.
- **Rohit's directory is a personal working tree.** Files date from 2019–2022
  with no guarantee of internal consistency, and some subdirectories are
  world-writable. We should treat it as strictly read-only and stage copies. He
  could also map figures to obsid/band/timestep directly, which would collapse
  most of the Phase 2 search — worth a conversation before that phase rather
  than before Phase 1.
- **Subtraction parameters may not be fully recoverable** from the paper text. If
  Phase 1 fails to converge, the fallback is asking Rohit for the script, which
  likely still exists alongside the CASA logs in `20151203_sub/161MHz`.
- **Scope of "reproduce".** Phases 1 and 2 answer the validation question at low
  cost. Phase 3 is the more rigorous claim and considerably more work. Worth
  deciding explicitly whether Phase 3 is required before Phase 5 starts, or
  whether a validated subtraction plus matching figures is enough to move on.
