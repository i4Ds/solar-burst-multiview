# P-AIRCARS: findings for the developers (draft for André)

Not sent. Two prepared branches in the Mac clone `~/Projects/P-AIRCARS`, both on
upstream `fa4aa91` (master, 1 Oct 2026), not pushed anywhere:

| branch | commits | scope |
|---|---|---|
| `upstream/slurm-fixes` | `7f0b575`, `2a137eb` | any Slurm run |
| `upstream/calibration-fixes` | `1cfb717`, `c17da8e` | self-cal without polcal; reusing calibrator tables on a rerun |
| `upstream/docs-slurm` | `cbc3d24` | docs: CLI names and options, worker size |

To publish: fork `devojyoti96/P-AIRCARS`, push a branch, open a PR. Each
commit message explains the change; commits are authored by André with
Claude as co-author.

Setup where this was found: calculon (FHNW), Slurm with two clusters (CPU
cluster `calc-cpu`, partition `cpu-daily`), login node Ubuntu 24.04, compute
nodes Rocky 9; P-AIRCARS installed in developer mode (`pip install -e .[dev]`),
`init-paircars-setup --init` on the login node, Prefect and Postgres there.
Data: MWA solar obs 1348547272 (G0002, 2022-09-30), calibrator 3C444
(1348574416), one coarse channel.

## 1. Slurm submission reads the Prefect config from the wrong directory

`submit_slurm_master_flow` (`paircars/clusterutils/slurm_cluster.py`, line 437)
loads `f"{get_cachedir()}/prefect_{scheduler_name}/prefect.config.npy"`, that
is `~/.paircarspipe/prefect_slurm`. Everything that writes this file
(`prefect_setup_utils.py`, `proc_manage_utils.py`, `prefect_server.py`) uses
`f"{get_datadir()}/{username}/prefect_{scheduler_name}"`.

On a clean setup, `run-mwa-paircars … --cluster` stops at once:

```
FileNotFoundError: [Errno 2] No such file or directory: '/home2/<user>/.paircarspipe/prefect_slurm/prefect.config.npy'
Error occured in executing P-AIRCARS master flow.
```

If an older install left a config there (3.0.6 used that path), the master job
gets that old `NODE_URL` instead and fails with "Could not reach prefect
server at: http://<old host>:4260/api from compute node." Fix (`7f0b575`): read
from `get_datadir()/<user>`, like the writers. (Also: `np.load` runs before the
`os.path.exists` check right below it, so the friendly message never shows.)

## 2. CPU accounting plugin is not registered on Slurm workers

Tasks in `paircars/pipeline/tasks.py` call `dask_client.run(get_worker_cpu_time)`
before and after each step. `get_worker_cpu_time` reads
`dask_worker.cpu_accounting_monitor`, which `CPUAccountingPlugin` sets.
The plugin is registered for the local cluster (`proc_manage_utils.py`, line 300)
but not for the two `SLURMCluster` clients in `slurm_cluster.py`. On Slurm,
basic calibration, self-calibration and applying solutions all failed at their
first task:

```
AttributeError: 'Worker' object has no attribute 'cpu_accounting_monitor'
```

which the log shows as "Error in spliting calibrator measurement sets" etc.
Fix (`2a137eb`): register the plugin after both `Client(cluster, …)` calls,
and return 0 from `get_worker_cpu_time` if the monitor is missing.

## 3. Calibration subflows

* **Self-calibration without polcal.** `selfcal_subflow` (`flows.py`) returns
  `selfcal_leakage`, which is only assigned under `if do_polcal:`. With
  `--no_polcal` a successful self-calibration then raises `UnboundLocalError:
  local variable 'selfcal_leakage' referenced before assignment`; the master
  flow treats self-cal as failed and images with the calibrator solutions only.
  Fix (`1cfb717`): initialise it to `[]`.
* **Reusing calibrator tables on a rerun.** `basic_cal_subflow` reuses existing
  calibrator tables only if there is a crossphase (`.kcrosscal`) table for
  every channel. When those are missing — always with `--no_polcal`, and
  probably also with polcal when no calibrator gives a crossphase solution
  ("No crosshand phase solutions obtained from any calibrators", which the
  master flow anticipates; untested) — the old set difference
  `coarse_chans - (bandpass_chans | crossphase_chans)` is empty. The subflow
  then logs "Calibrator solutions remains for coarse channels: []" and "No
  calibrator measurement set present", returns failure, and the master flow
  continues "solely using self-calibration", applying self-cal tables solved on
  calibrator-corrected data to uncorrected data. The same set difference also
  skipped channels that had only one of the two tables. Fix (`c17da8e`): a
  channel is done only when all required tables exist; crossphase tables are
  required only with polcal.

## 4. Smaller observations (no patch)

* GIF step in primary-beam correction: `ValueError: all input arrays must have
  the same shape` (the per-time PNGs differ in pixel size). The task then
  returns non-zero and the log says "Primary beam correction is failed",
  although all corrected FITS, HPC FITS and PNGs were written.
* Worker size defaults to 80 % of a node (`--cpu_frac/--mem_frac 0.8`). On a
  shared 384-core, 750 GB node that is 307 CPUs and 586 GB per worker. A note
  in the Slurm docs, or a per-worker default, would help.
* Docs vs code (branch `upstream/docs-slurm`, `cbc3d24`): `slurm.rst` and
  `initial_setup.rst` show `init-paircars-setup --datadir`, the code has
  `--configdir` (`init_data.py`), but `tests/pipeline/test_init_data.py` still
  passes `--datadir` — the developers should say which name is meant (keeping
  both as aliases would be friendliest). `slurm.rst` passes the target metafits
  as a second positional argument; the code wants `--target_metafits`.
  `slurm.rst` and `logger.rst` refer to `init-paircars-prefect status`; the
  command is `setup-paircars-prefect status`.
* Site specific, not P-AIRCARS: calculon's `/usr/local/bin/sinfo` wrapper adds
  `--clusters=all -O …`, which breaks `sinfo -o "%c %m"`. Worked around locally.

## Result once patched

Self-calibrated 4 s images of a type III burst at 143.4 MHz (2022-09-30
04:28:44): peak/rms 312, against 70 with calibrator solutions only.
