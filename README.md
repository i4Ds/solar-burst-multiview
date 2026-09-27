# solar-burst-multiview

MWA solar imaging for the
[solar-radio-imaging-spectroscopy](https://github.com/i4Ds/solar-radio-imaging-spectroscopy)
sabbatical. Reproduce Sharma et al. 2022 (ApJ 937, 99), then point the same
visibility-subtraction method at the 2024 MWA solar campaign.

This is not a multi-instrument project. STIX and e-Callisto live elsewhere.

## Status (27 September 2026)

| Phase | Gate | State |
|-------|------|--------|
| 0 Foundations | conda env, `src/solarburst/`, stage from calculon | done |
| 1 Subtraction | `python -m solarburst.subtract` vs Sharma `_sub.ms` | done (scan-mean, bit-exact) |
| 2 Figures | `python -m solarburst.figures` vs paper Figs 3, 5, 7, 9, 11, 12 | in progress (Fig 3 peaks within 15%) |
| 3 Re-image from visibilities | WSClean on calculon vs `new_ms/fits` | not started |
| 5 2024 campaign | config-driven run on archived `_ms.tar` | not started |

The paper’s 15 s running median is implemented as `--method running_median` but
was **not** what produced the validation `_sub.ms`. CASA logs show a scan-long
complex mean (`scan_mean`).

MWA containers (hyperdrive, birli, wsclean) run on calculon GPU nodes
(Singularity) and on CSCS (Podman).

## Package

Reusable code is `src/solarburst/` (`config`, `stage`, `subtract`, `maps`,
`bursts`, `figures`). Config: `configs/sharma2022.yaml`. Staged data:
`data/sharma2022/` (gitignored). Rebuilt figures: `figures/sharma2022/`.

```bash
conda env create -f environment.yml
conda activate solar-burst-multiview
pip install -e .
```

```bash
python -m solarburst.stage --check     # 1.2 GB validation MS pair (FHNW VPN)
python -m solarburst.subtract          # Phase 1 gate
python -m solarburst.figures           # Phase 2 figures
```

Machine setup (Miniforge, SSH to calculon, Zotero):
[docs/new-machine-setup.md](docs/new-machine-setup.md).

Calculon containers and Slurm:
[docs/calculon-mwa.md](docs/calculon-mwa.md).

Full reproduction mechanics:
[docs/reproduction-plan.md](docs/reproduction-plan.md).

## References

`references/core_references.bib` — Sharma 2022, Oberoi 2017, Mohan 2017, and the
other papers the conversion and imaging rest on. Rebuild with
`python scripts/resolve_references.py`.

## Related

- [i4Ds/solar-radio-imaging-spectroscopy](https://github.com/i4Ds/solar-radio-imaging-spectroscopy) — sabbatical umbrella and [project board](https://github.com/orgs/i4Ds/projects/18)
- [i4Ds/mwa-demo](https://github.com/i4Ds/mwa-demo) — non-solar MWA shell pipeline
- [i4Ds/Karabo-Pipeline](https://github.com/i4Ds/Karabo-Pipeline) — SKA / Karabo experiments
