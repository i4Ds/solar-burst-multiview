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

Useful for burst work: `--timerange`, `--freqrange`, `--image_timeres`, and
`--do_forcereset_weightflag`. ASVO/AOFlagger flags and zero weights cut out
solar bursts (see `src/solarburst/reflag.py`).

Workers are separate `cpu-daily` jobs; the master asks Slurm for at most
8 CPUs and 16 GB. Do not start a second run of the same observation while
one is in the queue.
