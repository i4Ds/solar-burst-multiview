# P-AIRCARS on calculon

Self-calibration runs on the CPU cluster (`calc-cpu`, partition `cpu-daily`).
This is not the Apptainer/Singularity stack in `docs/calculon-mwa.md`.

P-AIRCARS is installed in developer mode
([upstream instructions](https://p-aircars.readthedocs.io/en/latest/install_paircars.html#install-p-aircars-in-developer-mode)):
a clone at `~/paircars/P-AIRCARS` (commit `fa4aa91`, 1 Oct 2026, version
3.0.7), installed editable (`pip install -e ".[dev]"`) into
`~/paircars/miniforge3/envs/paircars_env`. That env was created with the
documented command (Python 3.10, GCC 14 compilers, cmake, pkg-config) by
`scripts/calculon/paircars-dev-install.sbatch` on `calc-cpu` (16 min,
6 Oct 2026). `env.sh` activates it; `PAIRCARS_ENV=paircars` selects the older
PyPI 3.0.6 env, which is kept. With `-e`, a `git pull` in the clone takes
effect without reinstalling.

Beam files and udocker images go to `/scratch/$USER/paircars`
(`--datadir`). The login node is Ubuntu 24.04.
CPU nodes are Rocky Linux 9.8. Upstream tests Ubuntu 22/24 and CentOS 7 only.
The 1 Oct init job showed that `casatools` and udocker run on Rocky.

## Slurm setup: init on the login node

Following the [Slurm page](https://p-aircars.readthedocs.io/en/latest/slurm.html),
`init-paircars-setup` runs on the login node (`calc-m-001`), not in a job: it
starts the Prefect server and its PostgreSQL (udocker, proot engine) there,
and they keep running for the worker jobs. Done on 6 Oct 2026:

```bash
source ~/paircars/env.sh
setsid nohup init-paircars-setup --init --configdir /scratch/$USER/paircars/meta \
  --emails andre.csillaghy@fhnw.ch > /scratch/$USER/paircars/logs/init-login-<date>.out 2>&1 &
```

The git version names the data flag `--configdir` (the docs say `--datadir`).
`--init` only downloads files missing from
`/scratch/$USER/paircars/meta/paircarspipe_data`. `setsid nohup` keeps the
servers alive after the ssh session closes.

| Service | Where | Port |
|---|---|---|
| Prefect server (API and dashboard) | `calc-m-001`, `0.0.0.0` | 4260 |
| PostgreSQL in udocker | `calc-m-001` | 5260 |

Workers reach Prefect at `http://calc-m-001:4260/api`. Checked from
`calc-c-001`: ping, ports 4260 and 5260 open, `/api/health` returns `true`.

`~/paircars/env.sh` points `SLURM_CLUSTERS` at `calc-cpu`. P-AIRCARS calls
`sbatch` and `sinfo` with no cluster flag, and `cpu-daily` is not on the GPU
cluster. `sinfo` then lists `cpu-debug` (1 h) and `cpu-daily` (1 day) on
`calc-c-001`…`007`.

**Postgres recovery race.** The first login-node init failed with "Server did
not respond within 3 minutes": `server.log` showed `CannotConnectNowError …
Consistent recovery state has not been yet reached`. The database left by the
1 Oct init job (killed at job end) was still in crash recovery when Prefect
started. Once Postgres had recovered, restarting only Prefect worked:

```bash
source ~/paircars/env.sh
setsid nohup python -u -c 'from paircars.utils.prefect_setup_utils import start_prefect_server; start_prefect_server(4260, 5260, scheduler_name="slurm")' \
  > /scratch/$USER/paircars/logs/prefect-start-<date>.out 2>&1 &
```

`start_prefect_server` always stops and restarts Postgres first (a clean stop
now, so no recovery). Logs: `…/paircarspipe_data/$USER/postgres.log` and
`…/paircarspipe_data/$USER/prefect_slurm/prefect_home/server.log`.

### Is it up?

```bash
ssh calculon 'ss -ltn | grep -E ":(4260|5260)\b"; curl -s http://calc-m-001:4260/api/health'
```

Dashboard from the Mac: `ssh -N -L 4260:localhost:4260 calculon`, then
<http://localhost:4260/dashboard>.

After a login-node reboot both services are gone; rerun the `start_prefect_server`
line above.

## A run

From the login node, with absolute paths. In the git version the target is a
directory of measurement sets, with the metafits and calibrator given by flag:

```bash
source ~/paircars/env.sh
run-mwa-paircars /full/path/to/target_ms_dir \
  --target_metafits /full/path/to/<obsid>.metafits \
  --cal_datadir /full/path/to/cal_ms_dir --cal_metafits /full/path/to/<calid>.metafits \
  --workdir /scratch/$USER/paircars/work/<obsid> \
  --outdir /scratch/$USER/paircars/out/<obsid> \
  --cluster --partition cpu-daily --max_worker 4 --walltime 12:00:00
```

Two calculon specifics:

* `/usr/local/bin/sinfo` is a site wrapper that adds `--clusters=all` and a
  fixed `-O` format; P-AIRCARS's `sinfo -h -p <part> -o "%c %m"` then fails
  ("Invalid job format specification"). `env.sh` puts `~/paircars/bin`
  first on `PATH`, where `sinfo` just runs `/usr/bin/sinfo`
  (`scripts/calculon/paircars-bin/sinfo`).
* Each worker job asks for `--cpu_frac` × `--mem_frac` of a node, 0.8 by
  default. A `cpu-daily` node has 384 CPUs and 750 GB, so the default is
  307 CPUs and 586 GB per worker. Use `--cpu_frac 0.05 --mem_frac 0.05`
  (19 CPUs, 37 GB) for one coarse channel.

* **Patched clone.** In `fa4aa91`, `submit_slurm_master_flow`
  (`paircars/clusterutils/slurm_cluster.py`) reads `prefect.config.npy` from
  `~/.paircarspipe/prefect_slurm`, while the server writes it to
  `<datadir>/<user>/prefect_slurm`. The stale 1 Oct config there sent the
  master job to `calc-c-001:4260` ("Could not reach prefect server … from
  compute node"). The clone carries a local commit `aec76b6` on branch
  `calculon-fixes` that reads `<datadir>/<user>`; check the batch script with
  `grep PREFECT_API_URL work/<obsid>/paircars_slurm_<id>.sh` (must say
  `calc-m-001`). Not yet reported upstream.
* **Second patch,** `2714d8e` on the same branch. Every task calls
  `get_worker_cpu_time` on the dask workers, but `CPUAccountingPlugin`, which
  sets `cpu_accounting_monitor`, was only registered for local clusters. On
  Slurm every subflow (basiccal, selfcal, applysol) failed at its first
  task with `AttributeError: 'Worker' object has no attribute
  'cpu_accounting_monitor'`, reported as "Error in spliting …" (7 Oct run
  `20261006075631629`). The patch registers the plugin on both Slurm clients and
  makes `get_worker_cpu_time` return 0 if it is missing.
* **Third patch,** `f210b08`. With `--no_polcal`, `selfcal_subflow`
  (`paircars/pipeline/flows.py`) never set `selfcal_leakage`. A successful
  self-calibration then ended in `UnboundLocalError`, and the pipeline
  imaged with the calibrator solutions only (run `20261007043048979`). The
  patch sets it to `[]` at the start of the subflow.
* **Fourth patch,** `86bb02a`. On a rerun, `basic_cal_subflow` only reused
  existing calibrator tables if a crossphase (`.kcrosscal`) table existed for
  every channel, but those are only made with polarisation calibration. With
  `--no_polcal` it then found nothing to do, reported failure, and the master
  flow went on "solely using self-calibration": self-cal tables solved on
  3C444-calibrated data applied to uncalibrated data. The patch requires
  crossphase tables only with polcal, and counts a channel as done only when
  all required tables exist.

* Not patched: the GIF step at the end of primary-beam correction fails
  ("all input arrays must have the same shape", PNGs of different sizes) and
  the task then reports "Primary beam correction is failed" although the
  corrected FITS, HPC FITS and PNGs are all written.

All four patches are on branch `calculon-fixes` of `~/paircars/P-AIRCARS`
(`git log fa4aa91..calculon-fixes`).
* Compute nodes cannot reach the remote logger ("Internet connection is not
  available for remote logging"), so progress emails may not arrive.

Useful for burst work: `--timerange`, `--freqrange`, `--image_timeres`, and
`--do_forcereset_weightflag`. ASVO/AOFlagger flags and zero weights cut out
solar bursts (see `src/solarburst/reflag.py`).

Workers are separate `cpu-daily` jobs; the master asks Slurm for at most
8 CPUs and 16 GB. Do not start a second run of the same observation while
one is in the queue.

## First working run: 2022-09-30 burst, 7 Oct 2026

Target 1348547272 ch112 (143.4 MHz), calibrator 3C444 (1348574416) ch112,
`--do_forcereset_weightflag --timerange 2022/09/30/04:28:30~2022/09/30/04:29:02
--image_timeres 4 --pol I --no_polcal --keep_calibrated_ms --cpu_frac 0.05
--mem_frac 0.05 --max_worker 1`. Calibration on 3C444 took 16 min,
self-calibration 8 min, applying and imaging about 15 min.

At 04:28:44, primary-beam corrected Stokes I, beam 2.5′ × 1.3′:

| | peak (Jy/beam) | off-Sun rms | peak/rms | peak position |
|---|---|---|---|---|
| 3C444 only (run `20261007043048979`) | 4.9e5 | 7.0e3 | 70 | (+331″, +101″) |
| 3C444 + self-cal (run `20261007142908205`) | 1.13e6 | 3.6e3 | 312 | (+306″, +101″) |

Products: `/scratch/$USER/paircars/out/1348547272/20220930/1348547272_target/`
(`imagedir_…_basiccal_only` and `calibrated_ms_basiccal_only` are the 3C444-only
run). Comparison with hyperdrive + wsclean:
`figures/flare20220930/paircars_vs_hyperdrive_042844.png`.
