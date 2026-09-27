# MWA containers on calculon

André's CSCS stack, run under the container runtime calculon already has.
Besso uses Podman inside an `srun --partition=a100` shell. Calculon CPU nodes
have Apptainer and GPU nodes have Singularity-CE, so the same Docker images
are stored as SIF files and launched with `singularity exec --nv`.

The login node cannot run containers. Pulls and the smoke test are Slurm jobs.

## Images

| SIF | Docker URI | What it is |
|---|---|---|
| `~/mwa/images/mwa-demo_cuda12.5.1.sif` | `docker://mwatelescope/mwa-demo:cuda12.5.1` | Official stack. Hyperdrive base plus birli, giant-squid, wsclean, EveryBeam, IDG, CHIPS, AOFlagger, SSINS. [Dockerfile](https://github.com/MWATelescope/mwa-demo/blob/main/Dockerfile). |
| `~/mwa/images/hyperdrive_0.6.1-autos-cuda12.5.1-ubuntu24.04.sif` | `docker://mwatelescope/hyperdrive:0.6.1-autos-cuda12.5.1-ubuntu24.04` | Image used in the interactive `hyperdrive vis-sim` notes. |
| `~/mwa/images/sp5505_sha-967aa66-pass.sif` | `docker://ghcr.io/d3v-null/sp5505:sha-967aa66-pass` | Swiss Karabo/Spack build: hyperdrive, wsclean, aoflagger, DP3. Same tag as on Daint and Besso. |

Build cache and temporary files go to `/scratch/$USER/mwa` (BeeGFS). The SIF
files sit in `$HOME` so both clusters see them.

## One-time setup

From a checkout on the calculon login node (FHNW VPN if you are off campus):

```bash
ssh calculon
cd ~/solar-burst-multiview   # or wherever the clone lives
bash scripts/calculon/submit-setup.sh
```

That copies `mwa-env.sh` to `~/mwa/` and submits `mwa-pull` on cluster
`calc-cpu`, partition `cpu-daily`. When that job finishes, submit the smoke
test:

```bash
bash scripts/calculon/submit-setup.sh --smoke-only
```

`mwa-smoke` runs on cluster `cluster`, partition `debug`, one GPU. It repeats
the vis-sim from the notes:

```bash
hyperdrive vis-sim \
  --beam-file=mwa_full_embedded_element_pattern.h5 \
  --metafits=1184702048.metafits \
  --output-model-files=1184702048.uvfits \
  --source-list=GGSM_updated.fits \
  --num-sources=1
```

Logs are `~/mwa/logs/`. The pull job writes a tool inventory (which of
`hyperdrive`, `birli`, `wsclean`, `giant-squid`, `aoflagger`, `DP3` each image
actually contains).

## Interactive GPU shell

```bash
ssh calculon
srun --cluster=cluster --partition=debug --gres=gpu:1 \
  --ntasks=1 --cpus-per-task=8 --mem=16G --time=00:30:00 --pty bash

singularity exec --nv ~/mwa/images/mwa-demo_cuda12.5.1.sif bash -l
```

`debug` allows 30 minutes. Longer imaging belongs on `performance` (1 day) or
`h200` (`--gres=gpu:h200:1`). Ask Slurm for enough CPUs that the memory
request stays under the partition's per-CPU cap (`MaxMemPerCPU` is 3200 MB on
`debug`).

## What is not this setup

Besso's `podman pull` / `podman save` / `podman run --gpus=all` sequence is the
CSCS form of the same images. Calculon has no Podman binary on the nodes we
can schedule. Batch integration on Daint and Besso is still the question for
Colin McMurtrie.
