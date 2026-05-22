# Solar Burst Multiview

Multi-instrument analysis of solar radio bursts combining:

- **MWA** — Murchison Widefield Array radio imaging
- **STIX** — Spectrometer/Telescope for Imaging X-rays (Solar Orbiter)
- **e-Callisto** — International solar radio spectrograph network

## Notebooks

| Notebook | Description |
|----------|-------------|
| [01_find_events](notebooks/01_find_events.ipynb) | Query STIX and MWA catalogs for coincident solar burst events |
| [02_ecallisto_spectra](notebooks/02_ecallisto_spectra.ipynb) | Download and inspect e-Callisto dynamic spectra |
| [03_mwa_imaging](notebooks/03_mwa_imaging.ipynb) | MWA data download, calibration, and imaging with WSClean |
| [04_multiview](notebooks/04_multiview.ipynb) | Combined multi-wavelength analysis and visualization |

## Setup

```bash
conda env create -f environment.yml
conda activate solar-burst-multiview
jupyter lab
```

## Related repos

- [i4Ds/STIX-MWA](https://github.com/i4Ds/STIX-MWA) — earlier scripts for STIX/MWA overlap finding
- [MWA demo pipeline](https://github.com/i4Ds/mwa-demo) — step-by-step MWA processing walkthrough
