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

## Experiment tracking: MLflow on calculon

One MLflow run per image in the experiment `archive-bursts` (set up 21 Oct):
params (obsid, calibrator, channel, 4 s window, pipeline settings, git commit from
`~/mwa/events/VERSION`), metrics (peak, off-Sun rms, peak/rms, half-max centroid,
beam, Rayleigh–Jeans T_B, half-max area in beams), artifacts (FITS, light curve,
P-AIRCARS montage). `event_image.sh` logs each new image at the end
(`scripts/calculon/log_event_mlflow.py`); older images can be logged by hand with
the same script.

- Store: `sqlite:///~/mwa/mlflow/mlflow.db`, artifacts `~/mwa/mlflow/artifacts`
  (home on the NAS, not /scratch). Environment `~/mwa/mlflow-venv`, built on the
  login node: compute nodes have Python 3.9, the login node 3.12.
- UI: `ssh calculon 'bash ~/mwa/events/mlflow-ui.sh'` (one worker, job runner
  off), then on the Mac `ssh -N -L 5000:localhost:5000 calculon` and
  <http://localhost:5000>. It listens on localhost of the shared login node, so
  other calculon users could reach it too.

Runs carry a readable name ("2024-12-25 04:51:45 type II, 162.5 MHz"), tags
(`event_date`, `burst_type`, `phase`, `project`, `tier`, `status` ok/check/bad), a
Markdown description, and the image figure with Stonyhurst grid made on calculon
(`event_figure.py`). Logging an image again updates its run. Per-event tags and
markers: `LOGARGS` in `event_image.sh`.

**Catalogue page** (for reading, MLflow stays the store):
`~/mwa/mlflow-venv/bin/python ~/mwa/events/build_catalogue.py` writes
`~/mwa/catalogue/` (sortable table and one card per image with image, MWA light
curve and GOES/STIX/e-Callisto context). Copied to the Mac and published as an
Artifact: https://claude.ai/artifact/QwU6ZtNBeVh7Vxuuip27qk (private).
