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
  --timeres 10 --freqres 0.16 --quack_timestamps 8 \
  --cpu_frac 0.5 --mem_frac 0.6
```

Result: _pending_.
