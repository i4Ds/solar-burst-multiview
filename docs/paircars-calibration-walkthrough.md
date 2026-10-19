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

Result (run 2026-10-19, checked with python-casacore):

- Two MSs, `calibrator_1111476056_ch_{113,114}_t_20150327072047_20150327072227.ms`
  (the time range is first to last timestamp centre).
- 6 channels each: 144.235–145.035 and 145.515–146.315 MHz. Raw channels
  1–6 and 9–14; the edge channels 0, 7, 8, 15 are gone.
- 11 timestamps × 8256 rows, autocorrelations kept. DATA identical to the
  raw MS for those channels: no averaging happened.
- `FLAG`: Tile103 fully flagged (1.55 %), by `clipzeros`; nothing else.
- `WEIGHT` = 1, and a `WEIGHT_SPECTRUM` column was added (`initweights`).

## A2. Flag the calibrator

Pipeline call (flows.py 352–375): `run_flag(..., datacolumn="data",
flag_calibrators=True, flag_bad_spw=False, flag_quack=False,
use_rflag=False, use_tfcrop=True, flagdimension="freqtime",
run_uvbinflagger=False, restore_flag=False)` → `flagging.main(...,
flag_bad_ants=True, flag_autocorr=False, flagbackup=False)`.
`flag_bad_spw` is False because the MS (160 kHz) is coarser than the
metafits `FINECHAN` (40 kHz), so edge channels are not flagged again.

What `single_ms_flag` (flagging.py 47) then runs, in order:
1. `flag_badants`: tiles with `Flag = 1` in the metafits (`get_mwa_bad_ants`,
   mwa_utils.py) → Tile103.
2. `flagdata(mode='clip', clipzeros=True)`.
3. `flagdata(mode='tfcrop', timefit='line', freqfit='poly',
   flagdimension='freqtime', timecutoff=max(4, threshold),
   freqcutoff=max(3, threshold))`, threshold 5.
4. `flagdata(mode='extend', growtime=80, growfreq=80, extendpols=True)`:
   flag a whole time row / channel if >80 % of it is already flagged, and
   all correlations if one is.
5. Flag summary written to `<outdir>/flag_summary/`.

The CLI defaults differ from the pipeline call (quack, bad-spw and flag
backup are on by default), hence the `--no_*` options:

```bash
cp -r /data/stepwise/cal /data/stepwise/cal_after_A1   # keep the A1 state
run-mwa-flag \
  /data/stepwise/cal/calibrator_1111476056_ch_113_t_20150327072047_20150327072227.ms,/data/stepwise/cal/calibrator_1111476056_ch_114_t_20150327072047_20150327072227.ms \
  /data/cal/1111476056.metafits \
  --workdir /data/stepwise/cal --outdir /data/stepwise/out \
  --datacolumn data --use_tfcrop --no_flag_bad_spw --no_flag_quack --no_flagbackup \
  --cpu_frac 0.5 --mem_frac 0.6
```

Result (2026-10-19): **no new flags.** Flag fraction 1.55 % before and after
(Tile103 only); the flag summary shows 0.78 % for every other tile, which is
their one baseline with Tile103. `DATA` unchanged.

The MS `HISTORY` table confirms what ran: `clip` (zeros), `tfcrop`
(timecutoff = freqcutoff = 5, flagdimension freqtime) and `extend`
(growtime = growfreq = 80). `flag_badants` writes no history entry; Tile103
was already flagged. So tfcrop ran and found nothing above its cutoff.
`scripts/paircars-walkthrough/plot_flag_check.py` shows the 11 × 6 plane per
baseline and an approximate outlier statistic (line fit in time, MAD σ; not
the CASA algorithm): median largest deviation ≈ 2.6σ, as expected for 66
noise-like samples; 39 of 16,002 baseline-polarisations exceed 5σ on that
approximation.

The HISTORY also shows how the sample was made: Birli 0.18.2 (cable-length,
digital-gain, PFB-gain and geometric corrections; AOFlagger with the
`mwa-default` strategy), then `flagdata(mode='unflag')` on the full MS.
So the AOFlagger flags, including Tile103, were removed before the sample was
published; the flat per-baseline phases in A0 are consistent with the cable
and geometric corrections.

## A3. Import the calibrator model (hyperdrive)

This is where the 29 Sep run failed. `import_model.py` 51–188:

1. Beam file: the `mwa_full_embedded_element_pattern_<kHz>.h5` closest to
   the MS channel width → `_160.h5`. Sky model: `GGSM.txt` (WSClean/hyperdrive
   text format) in the P-AIRCARS data directory.
2. `hyperdrive vis-simulate -m <metafits> --beam-file … --middle-freq <MS mean>
   --freq-res 160 --time-res 10 --source-dist-cutoff <FWHM FoV in deg> -s GGSM.txt
   -n 1000 --num-fine-channels 6 --num-timesteps 11 --output-autos
   --output-model-files <ms>_model.ms`, run in the `paircarshyperdrive`
   udocker container. The brightest 1000 GGSM sources within the field of view,
   attenuated by the FEE beam, predicted as visibilities.
3. `setjy(standard='manual', fluxdensity=[1,0,0,0], usescratch=True)` only to
   create a `MODEL_DATA` column, then `MODEL_DATA` ← `DATA` of the model MS
   (`putcol`, no check of row order or shape).
4. `.modeling_succeed` / `.modeling_failed` marker in the MS.

The pipeline log only recorded "Total failure: 6". The CLI with `--verbose`
should show hyperdrive's own error.

```bash
cp -r /data/stepwise/cal /data/stepwise/cal_after_A2
run-mwa-import-model \
  /data/stepwise/cal/calibrator_1111476056_ch_113_t_20150327072047_20150327072227.ms,/data/stepwise/cal/calibrator_1111476056_ch_114_t_20150327072047_20150327072227.ms \
  /data/cal/1111476056.metafits --workdir /data/stepwise/cal \
  --cpu_frac 0.5 --mem_frac 0.6 --verbose 2>&1 | tee /data/stepwise/a3_import_model.log
```

Result: _pending_.
