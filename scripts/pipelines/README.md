# Three quiet-Sun imaging pipelines

One Python file per column. Shared drawing:
`python scripts/pipelines/diagram.py` → `figures/pipelines.png`.

| File | Column |
|---|---|
| `paper_2020.py` | Sharma & Oberoi 2020 published SuperUniform maps |
| `casa_remake.py` | This work, CASA 6.6 SuperUniform |
| `paircars.py` | P-AIRCARS |

```bash
python scripts/pipelines/paper_2020.py --demo
python scripts/pipelines/casa_remake.py --demo
python scripts/pipelines/paircars.py --demo
```

Walk through with pictures: `notebooks/06_quiet_sun_pipelines.ipynb`.
Handover: `docs/quiet-sun-handover.md`.
