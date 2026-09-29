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
CSCS form of the same images, and that stack is installed and working. Calculon
has no Podman binary on the nodes we can schedule; it uses SIF files and
`singularity exec --nv` instead.

## Laptop

The same three tools also run on the Mac, in a local Docker container named
`mwa` (Ubuntu 26.04 under Colima), with the repo mounted at `/work`. Homebrew
`birli` is broken (`libboost_system.dylib` missing from aoflagger) and is not
used. WSClean 3.7 in that container was not built with IDG, so imaging uses
`-gridder wgridder`. `MWA_BEAM_FILE` inside the container must point at
`data/mwa_full_embedded_element_pattern.h5`.

Notebooks: `notebooks/03_mwa_download.ipynb` talks to the archive.
`notebooks/03_mwa_imaging.ipynb` only reads files already under `data/<obsid>/`.

## Solar snapshot used to test the laptop stack

This is a pipeline test, not a Sharma reproduction. The scan was copied from
the shared calculon archive because the observation originally wanted was not
available. Local disk at the time held the Sharma 2015 tree and one 2017
uvfits (`1184702048`).

| | solar scan | calibrator |
|---|---|---|
| obsid | 1424757616 | 1424775768 |
| name | Oberoi2024B_Sun, project G0002 | Cal_solar_PicA, project D0006 |
| start | 2025-02-28 05:59:58 UTC | 2025-02-28 11:02:30 UTC |
| length | 176 s | 296 s |
| band | 24 picket coarse channels, centre 144 MHz | same channel list |

ASVO had already run birli 0.18.0. There are no raw gpubox files. Hyperdrive
had not been run. The notebook skips birli, solves on Pictor A
(`data/srclist_pica.yaml`, Jacobs et al. 2013), and applies those solutions
to the solar measurement set. Solving on the solar scan itself fails: the Sun
dominates and is not in that sky model.

What the images show, 29 September 2026:

- Before solutions, channel 113 is speckles at about 4 Jy/beam.
- After solutions the peak is about 2×10⁵ Jy/beam. The brightest pixel sits
  about 1.8° from the Sun, one grating lobe of the regular tile grid. The
  synthesised beam is about 2′. The optical disk (radius 16′) is at the phase
  centre and is not that ridge.
- Channels 107, 113, and 120 are 1.28 MHz spikes separated by about 8 MHz.
  A lobe at 1.6° shifts by only about 0.1° between them, so they stack.
  Three minutes of Earth rotation do not fill the uv plane.

The tools run. This snapshot does not become a solar disk. Self-calibration
on the Sun was not tried.
