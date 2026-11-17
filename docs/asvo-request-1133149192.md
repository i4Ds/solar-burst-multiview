# ASVO request: 0.5 s visibilities of 2015-12-03 (Figure 4)

Not submitted. Dry runs on 17 November 2026 accepted both parameter
sets (`no_rfi` included). Submit commands are below; do not run them
until André says so. Conversion jobs, measurement sets, delivery acacia.
Not gpubox files.

Goal: start Sharma & Oberoi (2020) Figure 4 from uncalibrated visibilities
at the paper cadence (570 × 0.5 s), then solve the gains ourselves on Cen A.

## What is already on the NAS (checked 17 November 2026)

| Observation | What we hold | Cadence | Use for Figure 4 |
|---|---|---|---|
| Sun `1133149192` | ASVO job 1113526, `1133149192_1113526_ms.tar` (25 G) | **4 s**, 160 kHz, AOFlagger off | No. That product cannot make 0.5 s maps. |
| 3C444 `1133161488` | ASVO job 1113527, `1133161488_1113527_ms.tar` (9.0 G) | **4 s**, 160 kHz, AOFlagger off | Yes, as an independent calibrator. Do not request again. |
| Cen A `1133139776` | Rohit's CASA tables only (`new_ms/cal_soln/*.cal.p`, 3.4 M) | — | No visibilities. Those tables were solved on his cotter measurement sets; they are not a starting point for a new Birli conversion. |

Rohit's `new_ms/` copies of the Sun are calibrated (`CORRECTED_DATA`). They
are what we have already imaged. They are not this request.

The 4 s Sun tar is the October P-AIRCARS comparison, not the 2020 pipeline.

## TAP, 17 November 2026 (`mwa.observation`)

All three are G0002, Phase I, quality Good, mode `HW_LFILES`, 24 coarse
channels `62,63,…,187,188` (same list as Rohit's nine bands), native
**0.5 s** and **40 kHz**. None is deleted. Gpubox files are in the archive.

| obs | name | start (UTC) | length | tiles | archived gpubox |
|---|---|---|---|---|---|
| 1133149192 | Sun | 03:39:35–03:44:31 | 296 s | 124 | 119 G (120 files) |
| 1133139776 | CenA | 01:02:39–01:04:31 | 112 s | 124 | 43 G (48 files) |
| 1133161488 | 3C444 | 07:04:31–07:06:23 | 112 s | 120 | 43 G (already converted) |

Those are the only two named calibrators on that morning (Cen A and 3C444).
Rohit used Cen A. We already hold 3C444 at 4 s.

Conversion cannot select coarse channels or a time range. Each job is the
whole observation.

## Proposed jobs (not yet submitted)

Conversion, not `submit-vis`. Native time is 0.5 s, and ASVO conversion
accepts `avg_time_res` from 0.5 s. Leaving that parameter out does **not**
give the correlator cadence (the 2022 MWAX test job 1109734 was delivered
at 2 s). Set it.

```text
Sun:  output=ms,avg_time_res=0.5,avg_freq_res=160,flag_edge_width=80,no_rfi=true
CenA: output=ms,avg_time_res=4,  avg_freq_res=160,flag_edge_width=80,no_rfi=true
```

- `avg_time_res=0.5` on the Sun: the Figure 4 cadence. About eight times the
  October 4 s tar → **~200 G**.
- `avg_time_res=4` on Cen A: same as the 3C444 product we already hold.
  Gain and bandpass solutions do not need half-second sampling. About **9 G**.
- `avg_freq_res=160`: same frequency grid as jobs 1113526/1113527, so 3C444
  and Cen A can be applied to the new Sun set. Figure 4 is MFS over 2.56 MHz;
  160 kHz is enough. Native 40 kHz would be about four times larger and is
  not required for these maps.
- `no_rfi=true`: no AOFlagger. Same as October. (Quiet Sun is less fragile
  than a burst, but we want an unflagged starting point.)
- No `apply_di_cal`: we solve Cen A (and, as a check, 3C444) ourselves.
- `flag_edge_width=80`: 80 kHz at each coarse-channel edge, as in October.

Gpubox (`submit-vis`) is the 119 G + 43 G archive copies. That is smaller
than a 0.5 s / 40 kHz measurement set of the whole band, but we do not need
native frequency, and we already convert with ASVO/Birli. Conversion is the
request.

## Commands (key stays in `~/.config/mwa_asvo/api_key` on calculon)

Dry run, then submit. Each is a one-minute job on `calc-cpu`. Dry runs
216525 (Sun) and 216526 (Cen A) printed the JSON below and did not
submit. Do not run the submit lines until André says so.

```bash
# Sun, 0.5 s — dry run
ssh calculon 'cd ~/mwa && sbatch -M calc-cpu -p cpu-daily --time=00:10:00 -n1 -c1 --mem=1G -J asvo-dry-sun -o logs/%x_%j.log --wrap "source ~/mwa/mwa-env.sh; export MWA_ASVO_API_KEY=\$(<~/.config/mwa_asvo/api_key); singularity exec \$MWA_DEMO_SIF giant-squid submit-conv -nv -p output=ms,avg_time_res=0.5,avg_freq_res=160,flag_edge_width=80,no_rfi=true 1133149192"'

# Cen A, 4 s — dry run
ssh calculon 'cd ~/mwa && sbatch -M calc-cpu -p cpu-daily --time=00:10:00 -n1 -c1 --mem=1G -J asvo-dry-cena -o logs/%x_%j.log --wrap "source ~/mwa/mwa-env.sh; export MWA_ASVO_API_KEY=\$(<~/.config/mwa_asvo/api_key); singularity exec \$MWA_DEMO_SIF giant-squid submit-conv -nv -p output=ms,avg_time_res=4,avg_freq_res=160,flag_edge_width=80,no_rfi=true 1133139776"'

# Submit (only after the dry runs print the parameter JSON and no error)
ssh calculon 'cd ~/mwa && sbatch -M calc-cpu -p cpu-daily --time=00:10:00 -n1 -c1 --mem=1G -J asvo-sub-sun -o logs/%x_%j.log --wrap "source ~/mwa/mwa-env.sh; export MWA_ASVO_API_KEY=\$(<~/.config/mwa_asvo/api_key); singularity exec \$MWA_DEMO_SIF giant-squid submit-conv -p output=ms,avg_time_res=0.5,avg_freq_res=160,flag_edge_width=80,no_rfi=true 1133149192"'
ssh calculon 'cd ~/mwa && sbatch -M calc-cpu -p cpu-daily --time=00:10:00 -n1 -c1 --mem=1G -J asvo-sub-cena -o logs/%x_%j.log --wrap "source ~/mwa/mwa-env.sh; export MWA_ASVO_API_KEY=\$(<~/.config/mwa_asvo/api_key); singularity exec \$MWA_DEMO_SIF giant-squid submit-conv -p output=ms,avg_time_res=4,avg_freq_res=160,flag_edge_width=80,no_rfi=true 1133139776"'
```

Once ASVO marks a job Ready, download to
`/mnt/nas05/data02/MWA_data/data/mwa_data2` with the existing retry job
(replace `JOBID` and `BYTES` from the Ready listing):

```bash
ssh calculon 'cd ~/mwa && sbatch -M calc-cpu --time=23:59:00 --export=ALL,JOBID=<id>,OBSID=1133149192,KIND=ms,BYTES=<n> ~/mwa/asvo-download-retry.sbatch'
ssh calculon 'cd ~/mwa && sbatch -M calc-cpu --time=23:59:00 --export=ALL,JOBID=<id>,OBSID=1133139776,KIND=ms,BYTES=<n> ~/mwa/asvo-download-retry.sbatch'
```

Do not request 3C444 again. Job 1113527 is already on disk at the same
160 kHz grid.

## After delivery (not started)

1. Extract the nine Figure 4 coarse-channel pairs (and Cen A on the same
   channels). Leave Rohit's tree untouched.
2. Solve Cen A. Apply those solutions to the 0.5 s Sun set. As a check,
   apply the existing 3C444 solutions as well.
3. Image 570 frames with the published `clean` settings (CASA 6.6 `tclean`
   in this installation). Then the Oberoi / Mohan kelvin stretch.

Rohit's `.cal.p` tables stay as a reference of *his* solutions, not as
input to the new measurement sets.
