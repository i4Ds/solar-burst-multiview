# Handover: Birli processing of the raw 0.25 s data of the 2022-09-30 burst

From: [claude] Claude Code session of 5–12 Oct 2026 (it keeps working on the
**2 s** data). To: a new Claude Code session that continues the **raw-data /
Birli** work towards 0.25 s images.

Read first: `docs/asvo-request-1348547272.md` (request, download, reviewed Birli
settings), `docs/calculon-mwa.md` ("Running jobs: what we learned"),
`docs/calculon-paircars.md`. Science context:
`solar-radio-imaging-spectroscopy/docs/handover-2022-09-30-science-results.md`.

## Goal

Images of the type III burst at **0.25 s**, the correlator's resolution (0.1 s does
not exist), at 148.5 MHz (coarse channel 116, the strongest), around the onset
**04:28:29–04:28:35 UTC** (at 2 s the brightest frame is 04:28:31). Source
≈ (+320″, +100″), ≈ 90–125″ SW of AR 13110.

## Where things stand

| step | status |
|---|---|
| ASVO raw-visibility job **1111033** (obs 1348547272, MWAX, 0.25 s, 10 kHz) | downloaded: `/mnt/nas05/data02/MWA_data/data/mwa_data2/1348547272_1111033_vis.tar`, 1,088,776,314,880 bytes, `DOWNLOAD_OK` (job 108715) |
| Settings for Birli | **reviewed with André** (12 Oct), see table below |
| Extract metafits + ch116 raw files | **done** (job 109786, 7.5 min): `/scratch/andre_csillaghy/mwa/flare20220930_raw/` holds `1348547272.metafits` and `1348547272_20220930042734_ch116_00{0..4}.fits` (4 × 11.0 GB + 1.2 GB) |
| Birli dry run | **done**, summary checked (below); log `~/mwa/logs/raw-birli_109786.log` |
| **Conversion** | **not started — needs André's explicit OK** |
| Checks after conversion | to do |
| Calibration and 0.25 s images | to do |

Job script: `scripts/calculon/raw-birli.sbatch` (installed as
`~/mwa/flare/raw-birli.sbatch`), stages `extract`, `dryrun`, `convert`:

```bash
ssh calculon 'cd ~/mwa && sbatch -M calc-cpu --mail-type=END,FAIL --mail-user=andre.csillaghy@fhnw.ch --export=ALL,STAGES=convert ~/mwa/flare/raw-birli.sbatch'
```

Output: `/scratch/andre_csillaghy/mwa/flare20220930_raw/1348547272_ch116_0.25s.ms`
(≈ 4.3 GiB; 16 CPUs, 64 GB, `--max-memory 48`).

## Reviewed Birli settings (Birli 0.18.1, mwa-demo image)

`--metafits … --provided-chan-ranges --no-rfi --flag-edge-width 80 --avg-freq-res 160 --max-memory 48 --no-draw-progress -M <out.ms> <ch116 gpubox files>`

- `--no-rfi`: AOFlagger flagged 95–98 % of the burst in the old ASVO 4 s
  products; with `no_rfi` the 2 s product had only dead tiles flagged (≈ 35 %).
- no `--avg-time-res` → native 0.25 s; `--avg-freq-res 160` → 8 × 160 kHz like
  all earlier products (a type III crosses 1.28 MHz in ≈ 10 ms).
- `--flag-edge-width 80` as in the 2 s ASVO product; metafits tile flags kept;
  quack time and DC flag at Birli defaults.
- Corrections: cable delay, digital gains, passband `auto` (MWAX, not
  oversampled), geometric delay; **no Van Vleck** (as in all ASVO products,
  for comparability; it affects amplitudes of very strong signals, not
  positions — a possible later experiment); no `--apply-di-cal`; phase centre
  from the metafits.

## Dry-run summary (checked)

- 1184 steps × 0.25 s = 296 s (04:27:34–04:32:30), all provided; quack 2.25 s
  (9 steps) flagged at the start.
- Only ch116 (148.48 MHz) selected; output 1.28 MHz = 8 × 160 kHz.
- 26 of 136 tiles flagged (metafits); 3,211 of 9,316 baselines (34.5 %).
- "Will not flag with aoflagger"; cable lengths, digital gains, coarse PFB
  passband ("auto (mwax, not oversampled)"), geometry corrected; Van Vleck not.
- Phase centre 12h24m35.70s −2°39′26.1″ (within ≈ 25″ of the Sun at 04:28:44);
  pointing 12h23m49s −5°32′55″.
- **Inconsistency to check:** the log header says
  `geometric corrections: applied=No, disabled=true`, the summary says
  "Will correct geometry." The archive reports `delaymode = NODELAYS`, so
  Birli must correct them.

## Checks after the conversion (before imaging)

1. TIME step 0.25 s, 1184 steps; 8 channels of 160 kHz around 148.48 MHz.
2. Flagged fraction ≈ 35 % overall, and **not higher during 04:28:29–04:29:05**
   (no burst flagging).
3. Flags per fine channel: edges and DC channel as expected.
4. Geometry: a quick dirty image (wsclean, a few seconds of data) must show a
   compact Sun-centred source, not smeared or offset; compare with the 2 s
   product of the same channel
   (`/scratch/andre_csillaghy/mwa/flare20220930_025s/1348547272_ch116.ms`, owned
   by the 2 s session — read only).
5. Amplitudes: averaged to 2 s, the light curve should match the 2 s product.

## Imaging plan (to agree with André)

- P-AIRCARS with its own calibration and self-calibration on the 0.25 s MS,
  `--image_timeres 0.25`, `--timerange 2022/09/30/04:28:29~2022/09/30/04:28:35`
  (24 images): `scripts/calculon/overnight/burst_series.sh` with
  `SRC_MS=<0.25 s MS>`, `METAFITS=…/flare20220930_raw/1348547272.metafits`,
  `TAG=1348547272_025s_ch116`, `TRANGE=…`, `TRES=0.25`.
- Expect peak/rms ≈ 100 (4× noisier than 4 s, where it was 465).
- Not yet checked: whether P-AIRCARS's **own** flagging (basic flagging, uvbin
  flagger) removes burst samples; read the target's `flag_summary/` after the
  run (`--no_uvbinflagger` exists).

## Coordination with the 2 s session

- Do not touch the 2 s data and products: `/scratch/andre_csillaghy/mwa/flare20220930_025s/`,
  `/scratch/andre_csillaghy/paircars/{data,work,out}/1348547272_2s_*`,
  `~/overnight/1348547272_2s_*`.
- Both sessions share the checkout `~/Projects/solar-burst-multiview`, branch
  `claude/flare-20220930` (PR #3). Work on your own branch, for example in a
  worktree, and pull before you commit:
  `git -C ~/Projects/solar-burst-multiview worktree add ../solar-burst-multiview-raw -b claude/flare-20220930-raw claude/flare-20220930`

## How to run things

- **calculon:** `ssh calculon`. If the name does not resolve on the VPN, use
  `ssh -o HostName=10.35.4.124 -o HostKeyAlias=calculon.informatik.fhnw.ch calculon`.
- **Login node:** only light commands. tar, du, Birli, analysis go into
  `sbatch -M calc-cpu -p cpu-daily … -o logs/%x_%j.log`; avoid `srun`.
  `squeue -M calc-cpu -u $USER`, `sacct -M calc-cpu …` (default cluster is the
  GPU one).
- **Containers:** `source ~/mwa/mwa-env.sh`;
  `singularity exec --bind /scratch $MWA_DEMO_SIF …` (birli, casacore, wsclean,
  hyperdrive); wsclean needs `--env OPENBLAS_NUM_THREADS=1`.
- **P-AIRCARS:** `source ~/paircars/env.sh` (env `paircars_env`, developer-mode
  clone `~/paircars/P-AIRCARS`, branch `calculon-fixes` with 4 local patches).
  Prefect :4260 and Postgres :5260 on the login node; check with
  `curl -s http://calc-m-001:4260/api/health`. Typical flags:
  `--do_forcereset_weightflag --pol I --no_polcal --cpu_frac 0.05 --mem_frac 0.05 --cluster --partition cpu-daily --max_worker 1 --walltime 06:00:00`.
  Only the first range of a comma-separated `--timerange` is imaged; the GIF
  step fails harmlessly.
- **Unattended runs:** `setsid nohup` on the login node; progress in
  `~/overnight/<TAG>.md`; mail via 1-second Slurm jobs.
- **Plots on the Mac:** env `solar-burst-multiview`; `scripts/calculon/overnight/make_cube.py`
  and `montage.py` (cube → figure), `scripts/burst_movie.py`,
  `scripts/burst_movie_mwa.py`.

## Rules from André

- Do what he asks; when he says stop, stop everything (jobs included).
- Review settings that affect data (flags, averaging, calibration) with him
  **before** running them; the conversion waits for his OK.
- Push freely to his repos (solar-burst-multiview, STIX-MWA,
  solar-radio-imaging-spectroscopy). **Never push to P-AIRCARS on GitHub**; its
  push URL is disabled in both clones. He contacts its developers himself.
- Write so that colleagues understand; say what is measured and what is assumed.
