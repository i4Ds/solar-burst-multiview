# MWA containers on calculon

André's CSCS stack, run under the container runtime calculon already has.
Besso uses Podman inside an `srun --partition=a100` shell. Calculon CPU nodes
have Apptainer and GPU nodes have Singularity-CE, so the same Docker images
are stored as SIF files and launched with `singularity exec --nv`.

The login node cannot run containers. Pulls and the smoke test are Slurm jobs.
Listing or extracting ASVO tarballs (`tar -t`, `tar -x`) reads gigabytes from
the NAS; run it inside a job or an `srun`, not on the login node.

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
srun --partition=debug --gres=gpu:rtx2080:1 \
  --cpus-per-task=4 --mem=12G --time=00:30:00 --pty bash

singularity exec --nv ~/mwa/images/mwa-demo_cuda12.5.1.sif bash -l
```

The GPU cluster is the default. CPU jobs need `sbatch -M calc-cpu` or `squeue -M calc-cpu`. Request a GPU by type (`gpu:rtx3080:1`, `gpu:rtx2080:1`, `gpu:rtxA4500:1`, `gpu:h200:1`). `debug` is one GPU and 30 minutes. See the [Calculon job guide](https://fhnw-hpc.pages.fhnw.ch/docs/runjobs/).

`debug` allows 30 minutes. Longer imaging belongs on `performance` (1 day) or
`h200` (`--gres=gpu:h200:1`). Ask Slurm for enough CPUs that the memory
request stays under the partition's per-CPU cap (`MaxMemPerCPU` is 3200 MB on
`debug`).

P-AIRCARS is a separate install. It does not use these SIF files. See
`docs/calculon-paircars.md`.

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
| band | 24 coarse channels, centre 144 MHz | same channel list |

ASVO had already run birli 0.18.0. There are no raw gpubox files. Hyperdrive
had not been run. The notebook skips birli, solves the Pictor A scan
against `data/GGSM_updated.fits`, and applies those solutions to the solar
measurement set. Each coarse channel is about 1.28 MHz, and that is a normal
bandwidth to image.

What was imaged on 29 September 2026, before the sky model was corrected to
`GGSM_updated.fits`:

- Before solutions, channel 113 peaked at about 4 Jy/beam.
- After solutions, channel 113 peaked at about 2×10⁵ Jy/beam. The synthesised
  beam was about 2′.
- Channels 107, 113, and 120 were also imaged together in a 2° field.

## 2022-09-30 M1.1 flare, first image

`scripts/calculon/flare-image.sbatch` images solar obs 1348545200 at the STIX
peak (03:57:23 UTC) with solutions from PKS0408-65 (1348522216, 6.4 h earlier).
Both tarballs sit in `/mnt/nas05/data02/MWA_data/data/mwa_data`. Each holds one
MS per coarse channel and the metafits. ASVO averaged them to 4 s and 160 kHz,
so one 4 s timestep is the shortest image. There is no coarse channel at
150 MHz; ch113 (144.6 MHz) matches the laptop test above.

The MS phase centre is already the Sun. If you compute the Sun's RA/Dec, keep
it in GCRS: `get_body(...).icrs` is barycentric and lands about 11° away.

`scripts/flare_overlay.py` resamples the wsclean image onto helioprojective
coordinates (`solarburst.maps.radec_to_hpc`, solar north up) and contours it on
AIA. At the peak the 144.6 MHz source sits on AR 13110 (+215″, +95″), not on the
M1.1 flare at the north-east limb (−867″, +397″).
