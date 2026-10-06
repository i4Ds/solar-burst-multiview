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
The init job is the check that `casatools` and udocker actually run on Rocky.

## One-time init

From a checkout on the login node, after the conda env exists:

```bash
bash scripts/calculon/submit-paircars.sh
```

That copies `paircars-env.sh` to `~/paircars/env.sh` and submits
`paircars-init.sbatch` on `calc-cpu`. The job needs network (Zenodo and the
udocker image registries) and about 20 GB under `/scratch/$USER/paircars`.
Log: `/scratch/$USER/paircars/logs/init-<jobid>.out`. It finishes with
`INIT_OK`.

`~/paircars/env.sh` points `SLURM_CLUSTERS` at `calc-cpu`. P-AIRCARS calls
`sbatch` and `sinfo` with no cluster flag, and `cpu-daily` is not on the GPU
cluster.

## A self-calibration job

Source the env on the login node and submit with `--cluster`. There is no
calibrator directory for a self-cal. Paths must be absolute.

```bash
source ~/paircars/env.sh
run-mwa-paircars /full/path/to/1424757616 \
  --workdir /scratch/$USER/paircars/work/1424757616 \
  --outdir /scratch/$USER/paircars/out/1424757616 \
  --cluster --partition cpu-daily \
  --max_worker 4 --walltime 12:00:00
```

The master script P-AIRCARS writes asks Slurm for at most 8 CPUs and 16 GB.
Workers are separate `cpu-daily` jobs. Prefect and its Postgres (udocker)
have to be up where those jobs can reach them. Init starts them on the CPU
node that runs it; that node does not keep them after the job ends. A
self-cal launched on the login node starts them there if they are down.
The login node must be able to run udocker (proot). That part is still to
be confirmed on `calc-m-001`.

Do not start a second run of the same observation while one is in the queue.
