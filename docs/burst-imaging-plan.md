# One image per radio burst (plan item 7c, 19 October 2026)

Candidates and review pictures: i4Ds/STIX-MWA `_results/ecallisto_mwa_bursts/`
(gallery https://claude.ai/artifact/AK68oh8tXW15ZL1zSxU17d, private). Discussion:
umbrella issue #21.

## What each image is

- **One frequency for all bursts: coarse channel 127, 162.6 MHz.** It is in the
  standard G0002 picket fence (46 of the 56 reviewed obs; 13 of 16 Phase IIIb,
  9 of 11 earlier tier A) and the channel e-Callisto most often picks as best.
  Obs without ch 127 use the nearest channel and are flagged as not comparable.
- **4 s at the burst maximum at 162.6 MHz**, at least 8 s inside the obs. First
  estimate from ASSA at 162.6 MHz; the final 4 s from the MWA dynamic spectrum
  of ch 127 (`solarburst.dynspec`) once the data are on calculon. A burst that
  does not reach 162.6 MHz is marked, not moved to another channel.
- **P-AIRCARS self-cal**, ch 127, 4 s. Position check with hyperdrive on the
  first event only. Results in `docs/archive-events.md` (peak/rms, position,
  T_B, flags); parameters per event in `configs/events/<obsid>.yaml`.
- **No AOFlagger anywhere**: `no_rfi=true` in every ASVO conversion (the submit
  script refuses one without it), Birli with `--no-rfi`.

## Data: each observation once, all of it

Registry and ledger, `python -m solarburst.obsstore`:

| file | what |
|---|---|
| `configs/calculon_obs.csv` | every ASVO tar on the calculon NAS (`scan`; 15 Oct listing: 5,053 tars, 2,551 obsids) |
| `configs/asvo_jobs.csv` | every ASVO job we request, with params and state; jobs in flight count as data we have |
| `configs/asvo/wanted-2026-10.csv` | what we want, by batch (`scripts/asvo_wanted.py` from the STIX-MWA candidates) |

`plan` compares the wanted list with registry and ledger and prints only the
missing requests, as `sbatch` lines for `scripts/calculon/asvo-submit-retry.sbatch`
(at most 5 obsids per ASVO submission). Rules:

- Targets: raw visibilities (`submit-vis`), the whole observation. Every later
  product (other channels, 0.25 s) is made with Birli on calculon, so no target
  is requested twice.
- Calibrators: one conversion each, all channels, 2 s / 160 kHz, no AOFlagger
  (their raw archives are ~0.5 TB each). A calibrator shared by several events
  is requested once.
- Older tars whose parameters we do not know (Rohit's and earlier downloads)
  never count as a match: they may have AOFlagger on. This includes the 4 Oct
  conversions of 1419137296 and its calibrators (jobs 1106097–9, made without
  `no_rfi`).

| batch | events | targets | calibrators | archive size |
|---|---|---|---|---|
| 0 | 2024-12-25 type II (1419137296), end-to-end test | 1 | 1 | 0.15 TB |
| 1 | Phase IIIb (256 tiles) in the gallery | 16 | 9 | 1.09 + 4.32 TB |
| 2 | tier A of earlier phases (1348547272 raw already on calculon) | 10 | 9 | 4.20 + 4.20 TB |

Conversions come out much smaller than the archive size (10 kHz → 160 kHz).
6 Phase IIIb events have no same-channel calibrator within 24 h: P-AIRCARS
self-cal starts there from a calibrator with another channel set or a sky model.

## Downloads: the ASVO watcher

`scripts/calculon/asvo-watch.sbatch` (with `asvo_watch.py`, both copied to
`~/mwa/`) runs on calculon: every 30 min `giant-squid list`, and every Ready job
whose tar is not on the NAS with its full size is downloaded with
`asvo-download-retry.sbatch` (Slurm job `asvo-dl-<jobid>`, at most 3 at once,
into `mwa_data2`). It resubmits itself before its time limit and stops when
nothing is pending. Status: `~/mwa/asvo-watch.status`. Started 19 Oct (job 111483).
The ledger in git is updated from that status file, not by the watcher.

Embargo: ASVO accepted all G0002 targets (collaboration access); the 5 OA004
targets are refused until their release dates (open access: PI only).

## On calculon, once the data are there

One Slurm array task per image, built from `configs/events/*.yaml`:

1. calibrator jobs first, one per calibrator (shared ones once);
2. per event, `--dependency=afterok` on its calibrator: extract ch 127 from the
   tar → Birli (`--no-rfi`, 0.25 s native, 160 kHz) → MWA dynamic spectrum →
   P-AIRCARS 4 s image;
3. array limited to about 4 tasks at a time (`%4`): P-AIRCARS starts its own
   Prefect/Postgres per run and had a start-up race (`docs/calculon-paircars.md`);
   one work directory and one status file per task, no Slurm mail.

## Before anything runs

- Calculon reachable (VPN), then `obsstore scan` for a fresh listing with sizes,
  and `df` of `/mnt/nas05/data02` against batch 1 (≈ 1.4 TB after conversion).
- André submits (his ASVO key). After each submission the job ids go into
  `configs/asvo_jobs.csv`; downloads with `asvo-download-retry.sbatch`.
- Batch 0 first, end to end; batch 1 only after its image is checked.

## Products and the image board (22 Oct)

MLflow (tried 21-22 Oct) is removed: it showed only successful runs, could not
put images side by side, and gave no place for a verdict. In its place:

**Products.** One product = one observation, one coarse channel, one time window,
one time resolution, one calibrator; id `<obsid>_ch<channel>_<label>`.
`scripts/calculon/product_run.sh` makes one (same steps as `event_image.sh`, which it
replaces: wait for the tars, Birli `--no-rfi`, calibrator MSs, MWA light curve, window
if none given, P-AIRCARS via `burst_series.sh`). `TRANGE`, `TRES`, `LABEL`, `CH`, `CAL`
make series (more time steps), other channels and other calibrators the same kind of
run. The P-AIRCARS work directory includes the calibrator, so another calibrator is
calibrated from scratch. Registry `~/mwa/products/<product>.json` (parameters, state,
attempts), log `~/mwa/products/<product>.md` (one section per attempt). Lists of
products: `scripts/calculon/run_products.sh` (KEY=VALUE lines, `PAR` at a time).
The images made with `event_image.sh` were entered with `register_legacy.py`
(`legacy: true`, state read from `~/mwa/events/<obsid>.md`).

**Export.** `scripts/calculon/export_board.py` (`~/mwa/tools-venv`, numpy, astropy,
sunpy) writes `~/mwa/board/`: `board.json` (events with channel list and Stonyhurst grid;
products with state, attempts, per-frame peak / rms / centroid / beam / T_B, MWA light
curve) and `data/<product>.txt` (all frames, Stokes I cropped to +-1500 arcsec, int16
scaled per frame, base64: artifact pages serve no raw binary) for products with up to
10 frames; series with more frames become a movie instead (`movies/<product>.mp4` and
`_peak.png`, made with `scripts/burst_movie_mwa.py`: full Sun and a zoom on the
source at its brightest frame, Stonyhurst grid, peak curve; H.264 from imageio-ffmpeg,
remade only when the frames change). `product_run.sh` runs the export after each product.

**Board page** `scripts/board/index.html`, on the laptop (22 Oct; a claude.ai copy existed
briefly). `~/mwa-board/` holds the export (synced from calculon `~/mwa/board` by
`scripts/board/sync_board.sh` whenever the VPN is up; e-Callisto spectra made locally with
STIX-MWA `src/board_spectra.py`; page converted to pure ASCII by `asciify.py`) and the
viewer's `judgements.json` and `requests.json`. `scripts/board/serve_board.py` (standard
library) serves it at <http://localhost:8793> (8770 is taken by macOS sharingd) and stores
verdicts and requests. Two launchd agents: `ch.fhnw.mwa-board-server` (keeps the server
up), `ch.fhnw.mwa-board-sync` (every 30 min, skips without the VPN). Programs in
`~/mwa-board/bin/`.

Table: one row per event (image of the brightest run, GOES class, phase, project) with
its runs below (image, channel, window, time resolution, calibration, run time, state,
peak/rms, position, verdict); images open at full resolution. Per run: image with
contours and grid (or a movie for more than 10 frames), e-Callisto dynamic spectrum,
MWA contours on AIA 193 A with NOAA regions and PFSS lines, verdict, next-step request.
Compare: up to four runs on one grid, common or own scale. Claude reads `requests.json`,
runs the requests with `product_run.sh` and writes `state` and `reply` back.

## 1449551392: all channels, 2 s, whole obs (23 Oct)

André asked for every channel. The archive holds 12 of the 24 channels of this obs. Eleven are imaged in 2 s over the whole 120 s (`configs/products/allch_1449551392.txt`; ch 120 is the earlier `drift_f_ch120` run). Ch 220 (281.6 MHz) is left out because no calibrator with that channel was observed within ±10 days.

| channels | calibrator (3C444, +6.1 h) | ASVO job |
|---|---|---|
| 97 | Cal_3C444_Ch93 1449573272 | 1115936 |
| 120, 132 | Cal_3C444_Ch121 1449573328 | 1115661 |
| 138, 143, 146, 152 | Cal_3C444_Ch145 1449573384 | 1115937 |
| 158, 161, 167, 173 | Cal_3C444_Ch169 1449573440 | 1115930 |

- `scripts/calculon/start_allch.sh` runs the round:
  - one Slurm job extracts the 9 missing channels from the 50 GB tar;
  - after that, three product runs at a time.
- The drift movie `1449551392_ch161-158_drift_h` is built from two full-obs runs, ch 161 before 05:10:16 and ch 158 after. Composite parts can now carry a time span (`{"product", "from", "to"}`).
- Gpubox files are named with zero-padded channels (`_ch097_`), and `raw-birli.sbatch` and `product_run.sh` now pad the channel number.
