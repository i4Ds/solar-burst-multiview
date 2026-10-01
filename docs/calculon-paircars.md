# P-AIRCARS on calculon

Self-calibration runs on the CPU cluster (`calc-cpu`, partition `cpu-daily`).
This is not the Apptainer/Singularity stack in `docs/calculon-mwa.md`.

P-AIRCARS 3.0.6 (PyPI) is installed in a Miniforge env at
`~/paircars/miniforge3/envs/paircars` (Python 3.10, conda-forge compilers, as
in the upstream quickstart). Beam files and udocker images go to
`/scratch/$USER/paircars` (`--datadir` in the PyPI 3.0.6 package; the git tree calls the same flag `--configdir`). The login node is Ubuntu 24.04.
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
