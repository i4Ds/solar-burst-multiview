# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Environment

```bash
conda env create -f environment.yml
conda activate solar-burst-multiview
jupyter lab
```

Python 3.10 is required (CASA/mwalib compatibility). The conda env is named `solar-burst-multiview`.

External binaries needed for the MWA pipeline (notebook 03) — not in conda:
- `giant-squid` — MWA ASVO download client
- `birli` — MWA preprocessor (flagging, averaging)
- `hyperdrive` — MWA direction-independent calibrator
- `wsclean` — interferometric imager
- `$MWA_ASVO_API_KEY` must be set for downloads
- `$MWA_BEAM_FILE` must point to `mwa_full_embedded_element_pattern.h5`

## Architecture

This is a **notebooks-first exploration project** — there is no importable Python package yet. All science logic lives in `notebooks/`, run sequentially for a given event.

### Notebook flow

```
01_find_events       → identifies coincident STIX + MWA observations, saves data/coincident_events.csv
02_ecallisto_spectra → downloads e-Callisto dynamic spectra for the event window
03_mwa_imaging       → downloads MWA visibilities and runs the full calibration/imaging pipeline
04_multiview         → combines all three instruments into a single figure
```

### Key external libraries

| Library | Role |
|---------|------|
| `ecallisto-ng` (`ecallisto_ng`) | e-Callisto FITS download and spectrogram plotting. Entry points: `ecallisto_ng.data_download.downloader.get_ecallisto_data`, `get_instrument_with_available_data`; plotting via `ecallisto_ng.plotting.plotting.plot_spectogram_mpl` |
| `stixdcpy` | STIX flare catalog and light curve access from the STIX data center (`datacenter.stix.i4ds.net`) |
| `pyvo` | VO TAP queries against the MWA observation database (`vo.mwatelescope.org/mwa_asvo/tap`) |
| `mwalib` | Read MWA metafits for antenna/channel/timestep metadata |
| `astropy` | Time conversions (GPS ↔ UTC), FITS I/O, coordinate handling |
| `sunpy` | Solar coordinate frames if overlaying images on solar disk |

### Data directory

`data/` is gitignored (except `.gitkeep`). The MWA pipeline creates subdirectories per obsid:
```
data/<obsid>/raw/    ← gpubox files + metafits
data/<obsid>/prep/   ← birli uvfits output
data/<obsid>/cal/    ← hyperdrive solutions + calibrated MS
data/<obsid>/img/    ← wsclean FITS images
```

### Related repos

- [`i4Ds/STIX-MWA`](https://github.com/i4Ds/STIX-MWA) — earlier scripts for STIX/MWA event matching; reference for `find_flares_in_mwa.py` logic used in notebook 01
- [`i4Ds/mwa-demo`](https://github.com/i4Ds/mwa-demo) — the MWA shell-script pipeline that notebook 03 is based on; consult it for full birli/hyperdrive/wsclean flag options
- [`i4Ds/ecallisto_ng`](https://github.com/i4Ds/ecallisto_ng) — the ecallisto-ng source; `example/` notebooks show additional usage patterns
