# Handover — quiet-Sun pipelines (next Cursor agent)

Read this first. Then `AGENTS.md` and the newest entries of
`../solar-radio-imaging-spectroscopy/docs/agent-log.md` and
`docs/agent-tech.md`. Then open
`notebooks/06_quiet_sun_pipelines.ipynb` and run it.

Science question this work moves: **are quiet-Sun brightness temperatures
from MWA maps, at four metre-wave bands, close enough to Sharma & Oberoi
2020 Figure 4 that we can trust the same recipe on other quiet noon
days?** Faster path to an answer: one labelled pipeline at a time, with
a picture at each step, on data that are already on disk.

---

## How to behave

André is a scientist. Write in careful international academic English.
Lead with the fact. Show the maps. Keep imaging.

### Write this way

- Open with what a map **is**: day, time interval, method, what was
  averaged. Example: “26 March 2015, 03:46–03:51 UT, time-average of 586
  CASA SuperUniform 0.5 s brightness-temperature images.”
- Gallery lede: state what each scan’s maps actually are. “The 03:39 scan
  is Sharma & Oberoi 2020 Figure 4: published maps, our remake, and
  P-AIRCARS. The 03:49 scan is the noon pick: published SuperUniform FITS
  only.”
- Paper citations on the gallery (Sharma & Oberoi 2020). Call the
  products **published maps**, **published SuperUniform FITS**, **CASA
  remake**, **P-AIRCARS**.
- Brightness temperature on new pipeline figures: **MK**.
- Jobs, processes, watchers: **exited, terminated, timed out, cancelled,
  is not running**. Location: **runs on, is installed in, is stored in,
  is implemented in**.
- Headings: **date + time interval**. Pointing figure **after the maps**.
- If a job fails: log path, what ran, what to type next. Then type it.

### Keep doing

- **Always be imaging one event.** After you answer “what is running?”,
  the next sentence is the job you started or continued.
- Use visibilities that are already on disk (published MS, 0.5 s MS on
  scratch, NAS tars). André stopped 4 s conversion requests for 3
  December noon, 4 December, and 8 December.
- P-AIRCARS is its own column. The CASA remake uses the published
  phase-only bandpass tables and Haslam/Mohan flux.
- Isolated git worktree. Branch `cursor/<topic>`. Pull request. André
  merges. Gallery `i4Ds/mwa-quiet-sun`: push `main`.
- End the session with science in the umbrella `docs/agent-log.md` and
  machinery in `docs/agent-tech.md`. Trailer
  `Co-authored-by: Cursor <cursoragent@cursor.com>`.

### Standing constraints (facts)

- `figures/sharma2020/fig4.png` and the 2020 working tree stay as they
  are.
- STIX and e-Callisto stay in their own repositories.
- Empty catalogue days: metadata only. A row is mapped when a figure
  exists.
- `imaging.tb_scale: 9.48` belongs to the 2022 burst paper. Figure 4 uses
  Mohan F(ν).
- Shared checkout `~/Projects/solar-burst-multiview` on
  `cursor/sharma2020-fig4` already has a large uncommitted tree. Work in
  a temporary worktree. Leave that checkout alone.

### Open `@cursor:` from 20 November (umbrella log)

Still to do, in that order:

1. Whole-Sun flux per band, archive visibilities against the published
   measurement set, and one sentence on the 240 MHz value.
2. Baseline-length cut on one 217 MHz archive frame: which cut recovers
   the published restoring beam, and what it does to the peak.
3. Hold the 40 kHz Figure 4 conversion until (1) is done.

---

## The three pipelines

Software (one file each) under `scripts/pipelines/`. Picture:
`figures/pipelines.png`, rebuilt with `python scripts/pipelines/diagram.py`.
Step-by-step with visuals:
`notebooks/06_quiet_sun_pipelines.ipynb`.

| Column | File | What it does on the laptop |
|---|---|---|
| Sharma & Oberoi 2020 | `scripts/pipelines/paper_2020.py` | Published FITS → HISTORY → Mohan → time mean |
| CASA remake | `scripts/pipelines/casa_remake.py` | Our SuperUniform FITS → same Mohan → time mean |
| P-AIRCARS | `scripts/pipelines/paircars.py` | Cube → Jy/beam → Rayleigh–Jeans T_B |

```bash
conda activate solar-burst-multiview
python scripts/pipelines/diagram.py
python scripts/pipelines/paper_2020.py --demo
python scripts/pipelines/casa_remake.py --demo
python scripts/pipelines/paircars.py --demo
```

Cluster imaging (already written; do not fold it into the other column):

- CASA remake: `scripts/calculon/sharma2020_casa_snap.py` (Figure 4),
  `scripts/calculon/quiet_noon_casa_snap.py` (other noon scans),
  `scripts/calculon/quiet_noon_mean_tb.py`.
- P-AIRCARS: `scripts/calculon/overnight/burst_series.sh` with
  `TAG`, `SRC`, `CALDIR`, `TRANGE`, `TRES`, `MEMFRAC`, `WALL`, `LABEL`.

---

## Where the work stands (24 November 2026, morning)

**Running:** P-AIRCARS for 8 December 2015, 03:36–03:41 UT, 108 MHz.
Slurm 266429 on `calc-c-002` (master plus workers 266430–266432), Prefect
flow `paircars_20261124052104793`, work
`/scratch/andre_csillaghy/paircars/work/1133581016_ch84-85`,
log `main_paircars_20261124052104793.log`. Measurement set already in
`/scratch/andre_csillaghy/paircars/data/1133581016_ch84-85`. Watcher
`burst_series.sh` PID 2151603. `MEMFRAC=0.10`, `WALL=12:00:00`,
calibrator 1133571896, `TRANGE=2015/12/08/03:36:48~2015/12/08/03:41:28`,
`TRES=280`.

**Finished maps (show these):**

- 3 December 2015, 03:39–03:44 UT: published SuperUniform, CASA remake
  (mean of 570 × 0.5 s), P-AIRCARS (4 s, 3C444). Figure
  `figures/quiet2015/fig4_vs_paircars.png`.
- 3 December 2015, 03:49–03:54 UT: published SuperUniform FITS, Mohan
  mean. Peaks 1.15 / 1.43 / 1.39 / 0.78 MK.
- 4 December 2015, 03:50–03:55 UT: CASA remake, mean of 579 × 0.5 s.
  Peaks 0.29 / 0.33 / 0.51 / 0.70 MK. Flux still Oberoi 2017 Table 1 on
  this day; switch to Haslam at this pointing.
- 8 December 2015, 03:36–03:41 UT: CASA remake, Haslam at this pointing.
  Peaks 0.68 / 0.82 / 2.69 / 0.75 MK. At 217 MHz the peak is a compact
  source on the north-east limb.
- 26 March 2015, 03:46–03:51 UT: 586 CASA SuperUniform 0.5 s frames per
  band on scratch. Mohan 5σ kept 38 / 583 / 225 / 2 frames. Peaks 421 /
  3.85 / 368 / 360 MK. The 162 MHz panel used almost the whole scan.

**Failed, with the information needed to continue:**

- P-AIRCARS for 3 December 2015, 03:49–03:54 UT, 108 MHz. Dask
  `KilledWorker` on `run_target_split_jobs` (four workers, twice: selfcal
  then applysol), `mem_frac` 0.05. Log
  `/scratch/andre_csillaghy/paircars/work/1133149792_ch84-85/main_paircars_20261123125117424.log`.
  Same published 0.5 s MS. Next attempt: `MEMFRAC=0.10 WALL=12:00:00` as
  on 8 December. Source
  `/mnt/nas05/data02/rohit/20151203_MWA/new_ms/108MHz/1133149792_084-085.ms`,
  calibrator 3C444 `/scratch/andre_csillaghy/paircars/data/1133161488_ch84-85`,
  `TRANGE=2015/12/03/03:49:44~2015/12/03/03:54:24`.

**Next imaging order** (one event at a time): remaining 8 December
P-AIRCARS bands, then 4 December, then 3 December 03:49.

**Local data already staged** under `data/quiet2015/`: published FITS
(via `data/sharma2022/.../fits`, 570 frames per Figure 4 band), CASA
remake FITS `paper_casa_su/`, P-AIRCARS cubes
`1133149192_ch*_quiet.npz`, noon means `dec3_noon/`, `dec4/`, `dec8/`,
`march26/`. Flux JSON `paper_flux/*_full.json` (Haslam at the Figure 4
pointing).

**Gallery** `i4Ds/mwa-quiet-sun`. Generator `scripts/quiet_sun_site.py` →
`site/quiet-sun/`. Lede and first-name edits were local; publish them
when the pages are rebuilt. Pointing: Haslam 1982 polar sky, tile beam
90 / 9 / 0.9 %, yellow Sun, after the maps.

**NAS** `/mnt/nas05/data02/MWA_data/data/mwa_data2/` for local ASVO tars.
A 23-tar rsync from the laptop dropped twice (broken pipe); resume with
`--partial`.

---

## Git

Workhorse branch for this handover: `cursor/quiet-pipelines`. Do not
commit the dirty files already sitting in the shared
`cursor/sharma2020-fig4` checkout. Gallery and umbrella logs are separate
commits in their own worktrees.
