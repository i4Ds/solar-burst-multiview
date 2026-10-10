# P-AIRCARS on an Apple Silicon Mac

P-AIRCARS 3.0.7 calibrates and images MWA solar observations. Upstream
supports Ubuntu 22.04/24.04 and CentOS 7, Python 3.10 only. There is no
macOS arm64 wheel for `casatools`, and udocker's proot engine does not run
under Rosetta. This install hides that: Colima runs an Ubuntu 22.04
`linux/amd64` container, and a small patch set forces udocker onto fakechroot
and PostgreSQL onto TCP.

Tested on this laptop, 29 September 2026, against the Zenodo sample
(solar `1111474560`, calibrator `1111476056`). Intensity self-calibration
produced 24 Stokes IQUV cubes. Pictor A model import, polarisation
self-calibration, dynamic spectra, and EUV overlays did not succeed on this
setup. The images are self-calibrated, not flux-calibrated from the calibrator.

This is not the calculon install. Calculon keeps using the Singularity images
in [calculon-mwa.md](calculon-mwa.md).

## What you need

- Apple Silicon Mac, about 40 GB free. The beam files alone are about 12 GB,
  and the udocker images add several more. The Colima disk is 100 GB.
- [Colima](https://github.com/abiosoft/colima) and the Docker client:

```bash
brew install colima docker
```

- A clone of this repository, for the scripts. P-AIRCARS itself is cloned
  beside it on first setup.

The Colima profile is named `paircars` (8 CPUs, 16 GB RAM, Rosetta). It does
not replace a `colima` default profile you already use. Commands below pass
`--context colima-paircars` so they do not switch your current Docker context.

## Install

From this repository:

```bash
scripts/paircars-mac/setup.sh
```

That does four things:

1. Starts the `paircars` Colima profile if it is not already running.
2. Clones <https://github.com/devojyoti96/P-AIRCARS.git> to `../P-AIRCARS`
   (override with `PAIRCARS_ROOT`).
3. Creates `../P-AIRCARS-data` (`PAIRCARS_DATA`) and an Ubuntu 22.04
   container named `paircars`, with that checkout at `/opt/P-AIRCARS` and the
   data directory at `/data`.
4. Installs Miniforge, a Python 3.10 env, and `pip install ".[dev]"`, then
   runs `init-paircars-setup --init --configdir /data/meta`.

`init-paircars-setup` is the long step. On this machine the 40 kHz beam
interpolation took about 40 minutes, and the finer grids were faster. The
udocker image pull is a few gigabytes and is slow on the virtiofs mount.
The first PostgreSQL start fails, because the image fixes can only be applied
after udocker has extracted the images. The script applies those fixes and
runs init a second time. The second pass skips the beam build.

Python only, when the beam files and containers are already in place:

```bash
scripts/paircars-mac/setup.sh --skip-init
```

A shell in the container:

```bash
docker --context colima-paircars exec -u paircars -e HOME=/home/paircars \
  -it paircars bash -lc 'source /opt/miniforge3/etc/profile.d/conda.sh && conda activate paircars && bash'
```

## Sample observation

The published end-to-end sample is Zenodo record
[18641232](https://zenodo.org/records/18641232). Two archives, checksums
checked by `fetch-sample.sh`:

| File | Bytes | MD5 |
|---|---|---|
| `1111474560.tar.gz` | 375174986 | `b51b6f91b77f55a3f39eaef24fcc5a1f` |
| `1111476056.tar.gz` | 229578191 | `199524f180b90c526dffeeb83d9bdaf0` |

```bash
scripts/paircars-mac/fetch-sample.sh
scripts/paircars-mac/run-sample.sh
```

`fetch-sample.sh` unpacks the solar scan into `P-AIRCARS-data/target` and the
calibrator into `P-AIRCARS-data/cal`. Each directory has one metafits file and
three measurement sets (coarse channels 103–104, 113–114, 125–126). The solar
scan is 2015-03-27 06:55 UTC, 144 MHz, project G0002. The calibrator is
Pictor A, OBSID `1111476056`, 25 minutes later.

`run-sample.sh` calls `run-mwa-paircars` with one worker and half the CPUs,
which fits the 16 GB VM. The run on this laptop took about 23 minutes.
Products go to `P-AIRCARS-data/out/20150327/`. The log is
`P-AIRCARS-data/pipeline-work/main_paircars_*.log`.

The upstream README asks that papers cite Kansabanik et al. (2022, 2023, 2025)
and the code's Zenodo record. The sample itself is not for publication without
permission from the P-AIRCARS authors.

## Looking at the images

Cubes are FITS, Stokes IQUV, about 10 s and 1.28 MHz. To write PNGs with the
`solar-burst-multiview` environment:

```bash
conda activate solar-burst-multiview
python scripts/paircars-mac/render_pngs.py \
  ../P-AIRCARS-data/out/20150327/1111474560_target/imagedir_f_1.28_t_10.0_pol_IQUV_w_briggs_0.0/images
```

That writes `png/stokes_I_montage.png`, one `I_*.png` per cube, and
`png/IQUV_brightest.png`, zoomed to ±40 arcmin. The shared Stokes I scale is
0 to the 99.5th percentile.

## What the Mac run does not do

- Absolute flux calibration. Importing the Pictor A model failed for every
  coarse channel, so the pipeline continued with self-calibration only.
- Polarisation self-calibration. Q, U, and V in the cubes are not a leakage
  solution.
- Dynamic spectra and EUV overlays.
- Calculon. That install is `docs/calculon-paircars.md`, not this Colima setup.

The fakechroot and PostgreSQL changes live in
`scripts/paircars-mac/macos_fixes.py`. They edit the installed
`udocker_utils.py` inside the container and, after init, the extracted
PostgreSQL image. They are not changes to the upstream P-AIRCARS checkout.
