# ASVO request: 0.5 s visibilities for Sharma & Oberoi (2020) Figure 4

**Submitted 17 November 2026** (160 kHz) and **18 November 2026** (40 kHz).
Conversion jobs, measurement sets, delivery acacia. Not gpubox files.

| Observation | ASVO job | Parameters | Size | State |
|---|---|---|---|---|
| Sun `1133149192` | **1124199** | 0.5 s, 160 kHz, `no_rfi` | 50.9 GiB | Ready (17 Nov) |
| Cen A `1133139776` | **1124200** | 4 s, 160 kHz, `no_rfi` | 2.4 GiB | Ready (17 Nov) |
| Sun `1133149192` | **1124500** | 0.5 s, **40 kHz**, `no_rfi` | ~4× the 160 kHz tar | Submitted 18 Nov |
| Cen A `1133139776` | **1124501** | 4 s, **40 kHz**, `no_rfi` | ~4× the 160 kHz tar | Submitted 18 Nov |

Destination: `/mnt/nas05/data02/MWA_data/data/mwa_data2/`. Not the laptop.

Quiet scan `1133149192`, 2015-12-03 03:39:35–03:44:31 UT. Start from
uncalibrated visibilities at 570 × 0.5 s, in the four Figure 4 bands,
and solve the gains on Cen A.

| Figure 4 | Coarse channels | Centre |
|---|---|---|
| 108 MHz | 084–085 | 108.14 MHz |
| 162 MHz | 125–126 | 160.62 MHz |
| 217 MHz | 169–170 | 216.94 MHz |
| 240 MHz | 187–188 | 239.98 MHz |

ASVO conversion delivers all 24 coarse channels of the observation (the
service cannot subset). After download we keep these eight only.

## What is already on the NAS (checked 17 November 2026)

| Observation | What we hold | Cadence | This request |
|---|---|---|---|
| Sun `1133149192` | job 1113526, 25 G tar | **4 s**, 160 kHz | No. Cannot make 0.5 s maps. |
| Cen A `1133139776` | Rohit's `.cal.p` tables only (3.4 M) | — | No visibilities. Request. |
| 3C444 `1133161488` | job 1113527, 9.0 G tar | 4 s, 160 kHz | Not the Figure 4 calibrator. Do not request. |

Rohit's solar measurement sets are already calibrated. They are not this
request.

## TAP, 17 November 2026 (`mwa.observation`)

G0002, Phase I, quality Good, native **0.5 s** and **40 kHz**. The eight
Figure 4 channels are in the archived set. None is deleted.

| obs | name | start (UTC) | length | tiles | archived gpubox |
|---|---|---|---|---|---|
| 1133149192 | Sun | 03:39:35–03:44:31 | 296 s | 124 | 119 G |
| 1133139776 | CenA | 01:02:39–01:04:31 | 112 s | 124 | 43 G |

Rohit's calibrator for this scan is Cen A at 01:02 UT.

## Jobs submitted

```text
Sun:  output=ms,avg_time_res=0.5,avg_freq_res=160,flag_edge_width=80,no_rfi=true
CenA: output=ms,avg_time_res=4,  avg_freq_res=160,flag_edge_width=80,no_rfi=true
```

- `avg_time_res=0.5` on the Sun: Figure 4 cadence. Set it; omitting it is
  not native. The tar is the whole observation (~200 G). The four bands
  we keep are about **67 G**.
- `avg_time_res=4` on Cen A: gain and bandpass do not need half-second
  sampling. About **9 G**.
- `avg_freq_res=160`: Figure 4 is MFS over 2.56 MHz. Native 40 kHz is not
  required for these maps.
- `no_rfi=true`: no AOFlagger.
- No `apply_di_cal`: we solve Cen A ourselves.
- `flag_edge_width=80`: 80 kHz at each coarse-channel edge.

## Commands (key stays in `~/.config/mwa_asvo/api_key` on calculon)

Submitted 17 November 2026 as ASVO jobs 1124199 (Sun) and 1124200 (Cen A).
The 160 kHz choice was an agent default, not a match to Rohit's 40 kHz
sets. Native channelization is the 18 November request (jobs 1124500 and
1124501):

```text
Sun:  output=ms,avg_time_res=0.5,avg_freq_res=40,flag_edge_width=80,no_rfi=true
CenA: output=ms,avg_time_res=4,  avg_freq_res=40,flag_edge_width=80,no_rfi=true
```

The submit lines below are the record of the 17 November 160 kHz jobs.

```bash
# Sun, 0.5 s — dry run
ssh calculon 'cd ~/mwa && sbatch -M calc-cpu -p cpu-daily --time=00:10:00 -n1 -c1 --mem=1G -J asvo-dry-sun -o logs/%x_%j.log --wrap "source ~/mwa/mwa-env.sh; export MWA_ASVO_API_KEY=\$(<~/.config/mwa_asvo/api_key); singularity exec \$MWA_DEMO_SIF giant-squid submit-conv -nv -p output=ms,avg_time_res=0.5,avg_freq_res=160,flag_edge_width=80,no_rfi=true 1133149192"'

# Cen A, 4 s — dry run
ssh calculon 'cd ~/mwa && sbatch -M calc-cpu -p cpu-daily --time=00:10:00 -n1 -c1 --mem=1G -J asvo-dry-cena -o logs/%x_%j.log --wrap "source ~/mwa/mwa-env.sh; export MWA_ASVO_API_KEY=\$(<~/.config/mwa_asvo/api_key); singularity exec \$MWA_DEMO_SIF giant-squid submit-conv -nv -p output=ms,avg_time_res=4,avg_freq_res=160,flag_edge_width=80,no_rfi=true 1133139776"'

# Submit
ssh calculon 'cd ~/mwa && sbatch -M calc-cpu -p cpu-daily --time=00:10:00 -n1 -c1 --mem=1G -J asvo-sub-sun -o logs/%x_%j.log --wrap "source ~/mwa/mwa-env.sh; export MWA_ASVO_API_KEY=\$(<~/.config/mwa_asvo/api_key); singularity exec \$MWA_DEMO_SIF giant-squid submit-conv -p output=ms,avg_time_res=0.5,avg_freq_res=160,flag_edge_width=80,no_rfi=true 1133149192"'
ssh calculon 'cd ~/mwa && sbatch -M calc-cpu -p cpu-daily --time=00:10:00 -n1 -c1 --mem=1G -J asvo-sub-cena -o logs/%x_%j.log --wrap "source ~/mwa/mwa-env.sh; export MWA_ASVO_API_KEY=\$(<~/.config/mwa_asvo/api_key); singularity exec \$MWA_DEMO_SIF giant-squid submit-conv -p output=ms,avg_time_res=4,avg_freq_res=160,flag_edge_width=80,no_rfi=true 1133139776"'
```

Once a job is Ready, download to
`/mnt/nas05/data02/MWA_data/data/mwa_data2`:

```bash
ssh calculon 'cd ~/mwa && sbatch -M calc-cpu --time=23:59:00 --export=ALL,JOBID=<id>,OBSID=1133149192,KIND=ms,BYTES=<n> ~/mwa/asvo-download-retry.sbatch'
ssh calculon 'cd ~/mwa && sbatch -M calc-cpu --time=23:59:00 --export=ALL,JOBID=<id>,OBSID=1133139776,KIND=ms,BYTES=<n> ~/mwa/asvo-download-retry.sbatch'
```

## After delivery

The extracts sit under `/scratch/$USER/mwa/sharma2020/raw/`. Calibration
is CASA `applycal` of Rohit's Cen A bandpass tables
(`1133139776-%b*.cal.p` on the NAS), with `applymode=calonly` and
`calwt=False`, as in his `applycal.last`. Those tables are B Jones with
amplitude identically 1. P-AIRCARS is not used.

```bash
scp scripts/calculon/apply_0p5s_rohit_cal.py \
    scripts/calculon/sharma2020-apply-0p5s-rohit.sbatch \
    calculon:~/mwa/sharma2020/
sbatch -M calc-cpu ~/mwa/sharma2020/sharma2020-apply-0p5s-rohit.sbatch
```

Products: `/scratch/$USER/mwa/sharma2020/raw/cal_0p5s_casa/`. A 0.5 s
SuperUniform snapshot of the 108 MHz pair versus Rohit is
`scripts/calculon/compare_0p5s_snap.py`.
