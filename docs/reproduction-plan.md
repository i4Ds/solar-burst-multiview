# Plan: reproduce Sharma et al. 2022, then generalise

Status: **29 September 2026.** Phases 0–1 are done. Phase 2 is in progress.
A separate laptop trial imaged one 2025 solar snapshot from the shared archive
(section 6). The container stack runs; that scan does not make a solar disk.
`python -m solarburst.figures` rebuilds paper Figures 3, 5, 7, 9, 11 and 12.
Figure 3 peaks match the caption to 15%. Figures 7–12 use a 6σ MAD detector on
the `Tb_*_sub.p` cubes; they match the paper's layout and IDs, not Table 2
counts pixel-for-pixel.

This repo is MWA solar imaging only. STIX and e-Callisto are out of scope.

Goal, in two steps:

1. Reproduce the solar maps of Sharma et al. 2022 (ApJ 937, 99) as a validation
   exercise — do we understand the method well enough to regenerate its outputs?
2. Turn the visibility-subtraction imaging method into a reusable, config-driven
   tool and point it at the 2024 MWA solar observations.

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

### Software on calculon

The login node (`calc-m-001`, Ubuntu 24.04) still has no container runtime and
no GPU, and AppArmor blocks unprivileged user namespaces, so a rootless
runtime cannot be installed in `$HOME`. The compute nodes are different.
Surveyed 2026-09-27:

| where | runtime |
|---|---|
| CPU cluster `calc-cpu` | Apptainer 1.5.2 as `singularity`. Partitions `cpu-debug` (1 h) and `cpu-daily` (1 day). Images are pulled here. |
| GPU cluster `cluster` | Singularity-CE 4.3.1 with `--nv`, NVIDIA driver 610.57. Partitions `debug` / `performance` (RTX 2080 Ti, 3080, A4500) and `h200`. |

A SIF built by Apptainer on a CPU node runs under Singularity-CE on a GPU node.
`$HOME` (NFS, ~19 TB free), `/scratch` (BeeGFS, ~93 TB) and `/data` (~272 TB)
are mounted on both. There is no sudo. The account has a subuid/subgid range.

The images are the ones André runs on CSCS. On Besso that is Podman inside
`srun --partition=a100`; on calculon it is Singularity/Apptainer. See
[`calculon-mwa.md`](calculon-mwa.md).

| image | role |
|---|---|
| `mwatelescope/mwa-demo:cuda12.5.1` | the MWA stack: hyperdrive plus birli, giant-squid, wsclean, EveryBeam, IDG, CHIPS, AOFlagger, SSINS |
| `mwatelescope/hyperdrive:0.6.1-autos-cuda12.5.1-ubuntu24.04` | the image in the interactive `hyperdrive vis-sim` notes |
| `ghcr.io/d3v-null/sp5505:sha-967aa66-pass` | Swiss Karabo/Spack build (hyperdrive, wsclean, aoflagger, DP3), meant for Daint and Besso |

---

## 2. Where each piece of work runs

**New MacBook (M5 Pro, 2 TB, 64 GB)** — the Python work, and a Linux container
for the radio tools. Phases 1 and 2 (casacore, subtraction, figures) stay in
the conda env. `birli`, `hyperdrive`, and `wsclean` run in the Docker
container `mwa` (Ubuntu 26.04 under Colima), with the repo mounted at `/work`.
Homebrew builds of those tools are broken (`libboost_system.dylib` missing
from aoflagger) and are not used. WSClean 3.7 in that container has no IDG,
so imaging uses `-gridder wgridder`. The notebooks are
`notebooks/03_mwa_download.ipynb` (archive) and
`notebooks/03_mwa_imaging.ipynb` (local files only: set an obsid, paths come
from `data/<obsid>/`).

**Calculon** — anything needing WSClean, hyperdrive, birli or CASA proper:
re-imaging from visibilities, recalibration, and bulk processing of the 2024
archive. GPU nodes already run those tools from the MWA containers; the login
node does not. Operational steps are in [`calculon-mwa.md`](calculon-mwa.md).

**CSCS (Besso / Daint)** — the same images, via Podman rather than
Singularity. Installed and working: `srun --partition=a100
--gpus-per-task=1` then `podman run --gpus=all`. Calculon uses Slurm `sbatch`
and SIF files of those images.

---

## 3. Phased plan

Each phase ends at a gate that is checkable against Sharma's own products, so we
find out quickly if our understanding is wrong.

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

This is where reproduction becomes more than re-plotting. Take the calibrated MS
from `new_ms/<band>/`, apply our own subtraction, image it, and compare against
`new_ms/fits`.

The imaging stack is the Singularity images in [`calculon-mwa.md`](calculon-mwa.md).
Pull on `calc-cpu`, run on a GPU node with `singularity exec --nv`. The
`mwa-demo:cuda12.5.1` image is the one that contains wsclean and birli as well
as hyperdrive. A from-source build is only worth it if a tool is missing from
both that image and the Swiss Karabo image.

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
  and decide whether self-calibration on the Sun is needed. The 2025 trial in
  section 6 shows that transferring solutions from a calibrator scan works,
  and that a picket-fence snapshot still images as grating lobes.
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

- **Containers on the calculon login node.** Compute nodes already run
  Apptainer (CPU) and Singularity-CE (GPU). The login node cannot. Phase 3
  jobs have to be `sbatch`/`srun`, not login-node processes.
- **Rohit's directory is a personal working tree.** Files date from 2019–2022
  with no guarantee of internal consistency, and some subdirectories are
  world-writable. Treat it as strictly read-only and stage copies. Figure 7–12
  region centres and Table 2 counts are still approximate without his mapping.
- **Scope of "reproduce".** Phases 1 and 2 answer the validation question at low
  cost. Phase 3 is the more rigorous claim and considerably more work. Decide
  explicitly whether Phase 3 is required before Phase 5 starts, or whether a
  validated subtraction plus matching figures is enough to move on.
- **Picket-fence snapshots.** ASVO conversion products for later solar scans
  are narrow coarse channels with gaps, not a filled band. Short exposures of
  those cannot be turned into a solar disk by imaging settings. See section 6.

---

## 6. Laptop trial — one archive solar scan

Done 27–29 September 2026, on the Mac, in container `mwa`. This is not a
Sharma reproduction. It checks that download, calibration transfer, and
WSClean work on a scan taken from the shared calculon archive.

The scan was not chosen from a science search. The observation originally
wanted was not available. Local disk held the Sharma 2015 tree
(`data/sharma2022/`, about 1 TB) and one 2017 uvfits (`1184702048`). On
calculon, `/mnt/nas05/data02/MWA_data/data/mwa_data` holds the converted
archive. From a listing there, `1424757616_929853_vis_meta.tar` (Andrea
Zanelli) was copied across, together with the 7.2 GB visibility tar
`1424757616_922328_ms.tar`, and unpacked under `data/1424757616/`.

| | solar scan | calibrator |
|---|---|---|
| obsid | 1424757616 | 1424775768 |
| name | Oberoi2024B_Sun, project G0002 | Cal_solar_PicA, project D0006 |
| start | 2025-02-28 05:59:58 UTC | 2025-02-28 11:02:30 UTC |
| length | 176 s | 296 s |
| band | 24 picket coarse channels, centre 144 MHz | same channel list |

ASVO had already run birli 0.18.0 (digital gains, PFB gains, default
AOFlagger). There are no raw gpubox files, and hyperdrive had not been run.
The notebook therefore skips birli and solves on Pictor A.

What ran, and worked:

1. Fee beam file `data/mwa_full_embedded_element_pattern.h5`, exported inside
   the container as `MWA_BEAM_FILE`. Hyperdrive will not start without it.
2. Sky model `data/srclist_pica.yaml` (Pictor A nucleus, Jacobs et al. 2013:
   382 Jy at 150 MHz, spectral index −0.76).
3. `hyperdrive di-calibrate` on the calibrator measurement set.
4. `hyperdrive solutions-apply` onto the solar measurement set. Solving on
   the solar scan itself fails: the Sun dominates and is not in that sky model.
5. WSClean, 20″ pixels, `wgridder`. One channel, then channels 107, 113, and
   120 together in a 2° field. `show_images()` draws the optical solar limb.

What the images show:

- Before solutions, channel 113 is speckles at about 4 Jy/beam.
- After solutions the peak is about 2×10⁵ Jy/beam, so the calibration moved
  real flux. The brightest pixel sits about 1.8° from the Sun, one grating
  lobe of the regular tile grid. The synthesised beam is only about 2′. The
  optical disk (radius 16′) is at the phase centre and is not the bright ridge.
- Channels 107, 113, and 120 are 1.28 MHz spikes separated by about 8 MHz
  (roughly 137–154 MHz). A lobe at 1.6° shifts by only about 0.1° between
  them, so the three channels stack into the same stripe. A filled band would
  smear it. This picket fence has no filled band, and three minutes of Earth
  rotation do not fill the uv plane.

Nothing in the imaging settings removes that ridge. Self-calibration on the
Sun was not tried; it can tighten the core and cannot fill the missing
samples. This scan can still give a light curve or one image per channel.
A solar disk needs a continuous band or a much longer track.
