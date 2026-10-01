# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Environment

```bash
conda env create -f environment.yml
conda activate solar-burst-multiview
pip install -e .
```

The conda env is named `solar-burst-multiview` and tracks the latest CPython on conda-forge (`python` is unpinned in `environment.yml`).

This repo is MWA imaging: Sharma 2022 solar reproduction, plus the non-solar
MWA demo used to install birli / hyperdrive / wsclean on the laptop, calculon,
and CSCS. STIX and e-Callisto are out of scope.

Session notes for agents: `../solar-radio-imaging-spectroscopy/docs/agent-log.md`
(umbrella rules: `../solar-radio-imaging-spectroscopy/AGENTS.md`).

Reusable science code lives in `src/solarburst/`, installed editable. Stage data from calculon with `python -m solarburst.stage --check` (needs FHNW VPN).

MWA binaries (hyperdrive, birli, wsclean, giant-squid) are **not** in conda. On calculon they come from Singularity images under `~/mwa/images`, not from the login-node `PATH`. See `docs/calculon-mwa.md`. CSCS (Besso) runs the same images with Podman. `$MWA_ASVO_API_KEY` and `$MWA_BEAM_FILE` are only needed if downloading raw 2015 visibilities (Phase 4, optional).

## Architecture

Reusable logic lives in `src/solarburst/` (`config`, `stage`, `subtract`, `maps`, `bursts`, `figures`). Config is YAML under `configs/`. Remote paths are relative to Rohit Sharma's tree on calculon; `solarburst.stage` rsyncs named slices into `data/<event>/`.

```
python -m solarburst.stage --check   # 1.2 GB validation MS pair
python -m solarburst.subtract        # Phase 1 gate vs Sharma _sub.ms
python -m solarburst.figures         # Phase 2 gate: paper Figs 3, 5, 7, 9, 11, 12
```

`subtract` uses a scan-mean background (`scan_mean`). That matches Sharma's `_sub.ms` bit-exactly. `--method running_median` is the paper's §4.1 algorithm, not this ground truth.

`imaging.tb_scale: 9.48` recovers the pickled T_B scale; Rayleigh–Jeans from FITS `BMAJ`/`BMIN` is ~9.5× too low.

Notebooks under `notebooks/` are leftover drivers, not the current path.

### Key external libraries

| Library | Role |
|---------|------|
| `python-casacore` | Read/write CASA measurement sets (`casacore.tables`) |
| `sunpy` | Helioprojective frames and AIA overlay |
| `astropy` | Time conversions, FITS I/O, WCS |
| `reproject` | Map resampling |
| `pyyaml` | `configs/sharma2022.yaml` |
| `mwalib` | MWA metafits (antenna/channel/timestep metadata) |
| `pyvo` | VO TAP queries against `vo.mwatelescope.org/mwa_asvo/tap` (2024 archive) |

### Data directory

`data/` is gitignored (except `.gitkeep`). Sharma 2022 slices land under `data/sharma2022/`, preserving the relative layout of `remote.rohit_root`. Rebuilt figures go to `figures/sharma2022/`.

### Related repos

- [`i4Ds/solar-radio-imaging-spectroscopy`](https://github.com/i4Ds/solar-radio-imaging-spectroscopy) — sabbatical umbrella and org Project
- [`i4Ds/Karabo-Pipeline`](https://github.com/i4Ds/Karabo-Pipeline) — SKA / Karabo experiments
- [`MWATelescope/mwa-demo`](https://github.com/MWATelescope/mwa-demo) — upstream Docker image; the demo itself lives in this tree
