# Handover: continue with the 2 s data of the 2022-09-30 burst

From: [claude] Claude Code session of 5–12 Oct 2026 (it keeps the 0.25 s raw-data
work). To: a new Claude Code session that works on the **2 s** data.

Read first: `docs/progress-2026-10-09.md`, `docs/calculon-mwa.md` ("Running jobs:
what we learned"), `docs/calculon-paircars.md`, `docs/asvo-request-1348547272.md`.
Science context: `solar-radio-imaging-spectroscopy/docs/handover-2022-09-30-science-results.md`.

## Coordination with the other session

- **Do not touch** the 0.25 s work: `/scratch/andre_csillaghy/mwa/flare20220930_raw/`,
  `scripts/calculon/raw-birli.sbatch`, and any `raw-birli` Slurm job. Its
  conversion waits for André's OK.
- Both sessions share the checkout `~/Projects/solar-burst-multiview`, branch
  `claude/flare-20220930` (PR #3). Work on your own branch, for example in a
  worktree, and pull before you commit:
  `git -C ~/Projects/solar-burst-multiview worktree add ../solar-burst-multiview-2s -b claude/flare-20220930-2s claude/flare-20220930`

## The event and the data

- Type III burst at 04:28:30–04:29:05 UTC on 2022-09-30, ≈ 90–125″ SW of
  AR 13110, on open field lines; height ≈ 1.2 R☉. The larger M1.1 flare on the
  NE limb is radio-quiet.
- MWA obs **1348547272** (04:27:34–04:32:30, Phase II Extended, MWAX), 24 coarse
  channels ch101–187 (129–239 MHz). Calibrator 3C444 **1348574416** (same
  channel list, ASVO quality "Some Issues", 8.4 h later).
- **2 s data:** ASVO conversion job 1109734, `no_rfi=true`, 2 s × 160 kHz
  (8 fine channels per coarse channel), all 24 channels, flags = dead tiles only
  (≈ 35 %). Tar on calculon:
  `/mnt/nas05/data02/MWA_data/data/mwa_data2/1348547272_1109734_ms.tar` (20.8 GB;
  members `./1348547272_chNNN.ms/`, `./1348547272.metafits`).
- Already extracted: ch116 (148.5 MHz) and the metafits in
  `/scratch/andre_csillaghy/mwa/flare20220930_025s/` (the folder name says
  "025s" but holds the **2 s** MS).

## Done with the 2 s data

- P-AIRCARS run (job `20261010020210760`, ch116, 04:28:20–04:29:10, 2 s, Stokes I,
  no polcal), with its own 3C444 calibration and self-calibration:
  - data `/scratch/andre_csillaghy/paircars/data/1348547272_2s_ch116/`
  - work `/scratch/andre_csillaghy/paircars/work/1348547272_2s_ch116/`
  - output `/scratch/andre_csillaghy/paircars/out/1348547272_2s_ch116/20220930/1348547272_target/`
    (`caltables/`, `imagedir_f_1.28_t_2.0_pol_I_w_briggs_0.0/` with 25
    `pbcor_hpcs/*_HPC.fits`)
- Cube: calculon `/scratch/andre_csillaghy/overnight/analysis/1348547272_2s_ch116.npz`,
  Mac `data/flare20220930/overnight/1348547272_2s_ch116.npz`
  (`data[time, freq, y, x]`, Jy/beam, HPC grid ±2000″ at 20″).
- Figures in `figures/flare20220930/`: `paircars_burst2s_ch116.png`,
  `burst2s_ch116_aia.{mp4,gif}`, `burst2s_ch116_mwa.{mp4,gif}`, `*_peak.png`.
- Result: onset 04:28:29→04:28:31 (brightest frame, 1.15 × 10⁶ Jy/beam),
  sub-peaks 04:28:39 and 04:28:45, decay to background by 04:29:05; position
  stable at ≈ (+320″, +100″).

## Possible next steps with the 2 s data (André decides)

- 2 s series in more channels: the tar has all 24; extract with
  `tar -xf <tar> ./1348547272_chNNN.ms` **in a job**, then
  `scripts/calculon/overnight/burst_series.sh` with `SRC_MS`, `METAFITS`, `TAG`.
  The 4 s run showed ×100 flux jumps between neighbouring channels and failing
  ch173–187; check per-channel consistency.
- Onset timing across frequency at 2 s (type III drift), position vs time.
- MWA dynamic spectrum at 2 s from the 24 MSs (`src/solarburst/dynspec.py`).

## How to run things

- **calculon:** `ssh calculon`. If the name does not resolve on the VPN, use
  `ssh -o HostName=10.35.4.124 -o HostKeyAlias=calculon.informatik.fhnw.ch calculon`.
- **Login node:** only light commands. tar, du and any analysis go into
  `sbatch -M calc-cpu -p cpu-daily … -o logs/%x_%j.log`; avoid `srun`.
  `squeue -M calc-cpu -u $USER` / `sacct -M calc-cpu …` (the default cluster is
  the GPU one).
- **Containers:** `source ~/mwa/mwa-env.sh`; `singularity exec --bind /scratch $MWA_DEMO_SIF …`
  (casacore, wsclean, hyperdrive, birli). wsclean needs
  `--env OPENBLAS_NUM_THREADS=1`.
- **P-AIRCARS:** `source ~/paircars/env.sh` (env `paircars_env`, developer-mode
  clone `~/paircars/P-AIRCARS`, branch `calculon-fixes` with 4 local patches).
  Prefect :4260 and Postgres :5260 run on the login node; check with
  `curl -s http://calc-m-001:4260/api/health`. Typical flags:
  `--do_forcereset_weightflag --pol I --no_polcal --cpu_frac 0.05 --mem_frac 0.05 --cluster --partition cpu-daily --max_worker 1 --walltime 06:00:00`.
  Known: only the first range of a comma-separated `--timerange` is imaged; the
  GIF step fails harmlessly; polcal is untested on calculon. Restart Prefect
  only as in `docs/calculon-paircars.md` (needs the DB timeouts in `env.sh`).
- **Unattended runs:** `scripts/calculon/overnight/` (`burst_series.sh`,
  `make_cube.py`, `montage.py`), started with `setsid nohup` on the login node;
  progress in `~/overnight/<TAG>.md`, mail via 1-second Slurm jobs.
- **Plots on the Mac:** conda env `solar-burst-multiview`
  (`~/miniforge3/envs/solar-burst-multiview/bin/python`); `scripts/burst_movie.py`,
  `scripts/burst_movie_mwa.py`, `scripts/pfss_fieldlines.py`, `scripts/flare_overlay.py`.
  AIA files in `data/flare20220930/aia/`.

## Rules from André

- Do what he asks; when he says stop, stop everything (jobs included).
- Push freely to his repos (solar-burst-multiview, STIX-MWA,
  solar-radio-imaging-spectroscopy). **Never push to P-AIRCARS on GitHub**; its
  push URL is disabled in both clones. He contacts its developers himself.
- Review settings that affect data (flags, averaging, calibration) with him
  before running them.
- Write so that colleagues understand; say clearly what is measured and what
  is assumed.
