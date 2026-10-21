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
scaled per frame, base64: artifact pages serve no raw binary). `product_run.sh` runs
the export after each product.

**Board page** `scripts/board/index.html`, published with the export as
https://claude.ai/artifact/QwU6ZtNBeVh7Vxuuip27qk (private): table of all products
with state; per product a viewer (linear or log scale, grid, frame slider for series),
light curve with the window, context figure, a verdict (ok / check / bad, note) and a
next-step request (time series, more channels, other calibrator, other window).
Verdicts and requests live in the page's database (`judgements`, `requests`); Claude
reads them, runs the requests with `product_run.sh` and answers in the request
(`state`, `reply`). Compare: up to four products on one grid, common or own scale.
To refresh: export on calculon, copy `~/mwa/board` to the Mac with the page, publish.
