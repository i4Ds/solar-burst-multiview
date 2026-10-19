# P-AIRCARS calibration, step by step

A manual walk-through of the P-AIRCARS calibration block on the Zenodo sample,
one step at a time, so each intermediate product can be inspected. Started
2026-10-19 with André. Updated after each step.

- Setup: the Rosetta container from [paircars-mac.md](paircars-mac.md)
  (Colima profile `paircars`, container `paircars`, data at `/data`).
- Code: P-AIRCARS as installed in the container (`pip install`, not editable,
  patched by `scripts/paircars-mac/macos_fixes.py`). Line numbers below refer to
  the `calculon-fixes` checkout (395cdff) in `~/Projects/P-AIRCARS`.
- Paper: Kansabanik et al. 2023, ApJS, arXiv:2209.06666 (calibration block:
  §3, §4.1, Fig. 2).
- Data: target `1111474560` (2015-03-27), calibrator `1111476056` (Pictor A),
  coarse channels 103–104, 113–114, 125–126.
- Work directory for this walk-through: `/data/stepwise/` (the full run of
  29 Sep 2026 stays in `/data/pipeline-work` and `/data/out`).

Native arm64 (no Rosetta) is tracked separately in issue #6.

## Shell

```bash
colima start --profile paircars
docker --context colima-paircars start paircars
docker --context colima-paircars exec -u paircars -e HOME=/home/paircars \
  -it paircars bash -lc 'source /opt/miniforge3/etc/profile.d/conda.sh && conda activate paircars && bash'
```

## Order of the calibration block

From `paircars/pipeline/flows.py`. The pipeline calls Python functions; the
stand-alone CLI for each step is given in brackets.

| # | Step | Code | CLI |
|---|---|---|---|
| A1 | Split calibrator, 10 s / 160 kHz | `basic_cal_subflow`, flows.py 247–275 | `run-mwa-split` |
| A2 | Flag calibrator | flows.py 335 | `run-mwa-flag` |
| A3 | Import model visibilities (hyperdrive) | flows.py 422 | `run-mwa-import-model` |
| A4 | Gain and bandpass solve | flows.py 489 | `run-mwa-basic-cal` |
| B1 | Split target for self-cal, move phase centre to Sun | `selfcal_subflow`, flows.py 886 | `run-mwa-split --move_solarcenter` |
| B2 | Apply calibrator solutions | flows.py 1018 | `run-mwa-apply-basiccal` |
| B3 | Solar sidereal-motion correction | flows.py 1125 | `run-mwa-solar-siderealcor` |
| B4 | Intensity, then polarisation self-cal | flows.py 1184 | `run-mwa-selfcal` |
| C1–C4 | Split target, apply basic + self-cal, flag corrected data | `applysol_subflow`, flows.py 1482–1776 | `run-mwa-split`, `run-mwa-apply-basiccal`, `run-mwa-apply-selfcal`, `run-mwa-flag` |

In the full run of 29 Sep 2026, A3 failed for all 6 channels (log gives only
"Total failure: 6"), so there were no calibrator solutions; B4 intensity
self-cal succeeded on all 6, polarisation self-cal failed on all 6.

## A0. The raw calibrator visibilities

Read directly from the `DATA` column of `/data/cal/1111476056_ch113-114.ms`
with `scripts/paircars-walkthrough/plot_raw_vis.py` (python-casacore).
Plots (not committed; the sample is not for publication):
`P-AIRCARS-data/stepwise/plots/00_raw_vis_*.png`.

- ASVO output, already averaged: metafits `INTTIME` 0.5 s and `FINECHAN`
  40 kHz → MS at 10 s and 160 kHz. 11 timestamps × 8256 rows (128 tiles with
  autocorrelations). Picket-fence observation, 24 coarse channels in 12 pairs
  (`CHANNELS` 62 … 188); this MS is the pair 113/114 (144.0–146.56 MHz).
- Pointing az 135°, alt 59.8° (sweet-spot grid); phase centre on Pictor A.
  Sun 81.7° away at altitude 37°. `QUACKTIM` 3 s.
- Tile103 (antenna index 74) is all zeros. It is flagged in the metafits
  but the MS `FLAG` column is entirely false, so nothing is flagged yet.
  The split's `clipzeros` and step A2 will catch it.
- Cross-correlation spectrum: the first and last 160 kHz channel of each
  coarse channel are ~15–20 % low (filterbank roll-off). These are the
  channels the split drops.
- Phases per baseline are roughly flat across the 2.56 MHz, but each baseline
  sits at its own offset (instrumental gain phases φᵢ − φⱼ), so phase vs
  baseline length is scrambled. That offset is what the gain solve removes.
- Baseline matrix shows block structure by receiver group and a few
  low-amplitude tiles: per-tile gain differences before calibration.

## A1. Split the calibrator

Pipeline call: `run_target_split_jobs(..., datacolumn="data",
split_coarse_chans=coarse_chans, timeres=10.0, freqres=0.16,
prefix="calibrator", move_solarcenter=False, quack_timestamps=...)`.
`quack_timestamps = int(4.0 / timeres)` with the native time resolution
(`master_flow.py` 926).

```bash
show-paircars-ms /data/cal/1111476056_ch113-114.ms
run-mwa-split /data/cal/1111476056_ch113-114.ms /data/cal/1111476056.metafits \
  --workdir /data/stepwise/cal --prefix calibrator \
  --timeres 10 --freqres 0.16 --quack_timestamps 0 \
  --cpu_frac 0.5 --mem_frac 0.6
```

Result: _pending_.
