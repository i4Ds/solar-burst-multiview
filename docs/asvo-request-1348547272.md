# ASVO request: 0.25 s visibilities of obs 1348547272

**Submitted 9 Oct 2026, 15:18 (Mac, giant-squid 2.5.1): ASVO job 1109734, conversion,
state "Staging".** Parameters: `output=ms,avg_freq_res=160,flag_edge_width=80,no_rfi=true`
(no `avg_time_res` → 0.25 s), delivery acacia. Download to calculon once "Ready".

Goal: an image of the 2022-09-30 type III burst at its peak (04:28:44 UTC) at the
finest time resolution the data has. Our archive copy
(`1348547272_867321_ms.tar`) is averaged to 4 s and 160 kHz.

## What exists at ASVO (TAP, 9 Oct 2026)

| | |
|---|---|
| correlator | MWAX, **0.25 s**, 10 kHz |
| duration | 296 s (04:27:34–04:32:30 UTC) |
| channels | 24 coarse channels, ch101–187 (129–240 MHz, not contiguous) |
| raw files | 120 gpubox files, **1.09 TB** (≈45 GB per coarse channel), at Pawsey |
| quality | Good; 111 good tiles of 136 |

0.25 s is the limit: there are no data at 0.1 s.

## Proposed request

A conversion (Birli) job, not raw files. Conversion jobs cannot select coarse
channels or a time range, so the whole observation is converted.

```bash
export MWA_ASVO_API_KEY=...   # André's key
giant-squid submit-conv -n -p output=ms,avg_freq_res=160,flag_edge_width=80,no_rfi=true 1348547272   # dry run
giant-squid submit-conv    -p output=ms,avg_freq_res=160,flag_edge_width=80,no_rfi=true 1348547272   # submit
```

* `avg_time_res` left out → correlator resolution, 0.25 s (the parameter itself
  accepts only 0.5–32 s).
* `avg_freq_res=160` → 160 kHz, 8 fine channels per coarse channel, the same as
  the 4 s data and the hyperdrive/3C444 solutions.
* `no_rfi=true` → no AOFlagger. AOFlagger flagged 95–98 % of the burst in the
  4 s product; we flag dead tiles ourselves (`src/solarburst/reflag.py`).
* `flag_edge_width=80` (default) → 80 kHz flagged at each coarse-channel edge.
* No `apply_di_cal`: we calibrate with 3C444 ourselves.
* Delivery: default `acacia` (a download URL, tar).

## Expected size (estimate)

About 11 M rows (9316 baselines incl. autos × 1184 steps) per coarse channel.
At 8 channels × 4 polarisations: data, flags and weights ≈ 0.45 kB per row →
≈ 5 GB per coarse channel, **≈ 120–130 GB** for all 24 (one tar). The giant-squid
dry run or ASVO's job page gives the exact number.

## After delivery (not started)

1. Download to the calculon NAS with the existing STIX-MWA job
   (`scripts/calculon_asvo_download.sbatch`, writes to `mwa_data2`), not via the
   login node.
2. Extract ch116 (148.5 MHz, best signal at 4 s) and ch112 (143.4 MHz).
3. Reflag (dead tiles only), apply the existing 3C444 solutions, image
   0.25 s steps around 04:28:44 with wsclean, or run P-AIRCARS with
   `--image_timeres 0.25` reusing the 3C444 and self-cal tables.

## Commands (from the Mac; the key stays in `~/.config/mwa_asvo/api_key` on calculon)

Dry run, then submit (each a one-minute job on `calc-cpu`, giant-squid from the
mwa-demo image), then download to `/mnt/nas05/data02/MWA_data/data/mwa_data2`:

```bash
ssh calculon 'cd ~/mwa && sbatch -M calc-cpu -p cpu-daily --time=00:10:00 -n1 -c1 --mem=1G -J asvo-dryrun -o logs/%x_%j.log --wrap "source ~/mwa/mwa-env.sh; export MWA_ASVO_API_KEY=\$(<~/.config/mwa_asvo/api_key); singularity exec \$MWA_DEMO_SIF giant-squid submit-conv -n -p output=ms,avg_freq_res=160,flag_edge_width=80,no_rfi=true 1348547272"'
ssh calculon 'cd ~/mwa && sbatch -M calc-cpu -p cpu-daily --time=00:10:00 -n1 -c1 --mem=1G -J asvo-submit -o logs/%x_%j.log --wrap "source ~/mwa/mwa-env.sh; export MWA_ASVO_API_KEY=\$(<~/.config/mwa_asvo/api_key); singularity exec \$MWA_DEMO_SIF giant-squid submit-conv -p output=ms,avg_freq_res=160,flag_edge_width=80,no_rfi=true 1348547272"'
ssh calculon 'cd ~/mwa && sbatch -M calc-cpu --export=ALL,OBSIDS=1348547272 ~/mwa/asvo-download.sbatch'
```

The download job (`STIX-MWA/scripts/calculon_asvo_download.sbatch`, installed as
`~/mwa/asvo-download.sbatch`) waits for the ASVO job, runs at most 12 h and
resumes when started again. Log: `~/mwa/logs/asvo-dl-<jobid>.out`.

## Outcome (10 Oct 2026)

* **Job 1109734 delivered 2 s, not 0.25 s.** Downloaded to
  `/mnt/nas05/data02/MWA_data/data/mwa_data2/1348547272_1109734_ms.tar`
  (20.8 GB, 15 min). The MS has 148 × 2 s steps (04:27:35–04:32:29), 8 × 160 kHz,
  35 % flagged (dead tiles only: `no_rfi=true` worked). Leaving out
  `avg_time_res` does **not** give the correlator resolution; ASVO conversion
  jobs accept `avg_time_res` only from 0.5 s.
* **0.25 s needs the raw files.** Raw-visibility job **1111033**
  (`giant-squid submit-vis 1348547272`, whole observation, ≈ 1.09 TB) submitted
  10 Oct 10:00 (Mac), state "Staging". Plan: download to calculon only when
  ready, then Birli on calculon for ch116 at 0.25 s without AOFlagger.
* 2 s images of the burst: `scripts/calculon/overnight/burst_series.sh`
  (P-AIRCARS, ch116, 04:28:20–04:29:10, own calibration and self-cal).
* Raw job 1111033 "Ready" (1014 GiB) on 10 Oct; download started 12:25 as Slurm
  job 108698 on `calc-cpu` (`--time=23:59:00`, mail on end/fail), job ID passed
  instead of the obsid so the 2 s conversion is not fetched again:
  `sbatch -M calc-cpu --time=23:59:00 --export=ALL,OBSIDS=1111033 ~/mwa/asvo-download.sbatch`
  → `/mnt/nas05/data02/MWA_data/data/mwa_data2/1348547272_1111033_vis.tar`.
  Rerunning the same command resumes an interrupted download (`--keep-tar`).
