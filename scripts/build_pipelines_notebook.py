#!/usr/bin/env python3
"""Write notebooks/06_quiet_sun_pipelines.ipynb."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

from solarburst.config import REPO_ROOT

OUT = REPO_ROOT / "notebooks" / "06_quiet_sun_pipelines.ipynb"


def md(text: str) -> dict:
    text = text.strip("\n") + "\n"
    return {"cell_type": "markdown", "id": uuid.uuid4().hex[:8], "metadata": {}, "source": [text]}


def code(text: str) -> dict:
    text = text.strip("\n") + "\n"
    return {
        "cell_type": "code",
        "id": uuid.uuid4().hex[:8],
        "metadata": {},
        "execution_count": None,
        "outputs": [],
        "source": [text],
    }


cells = [
    md(
        """\
# Three quiet-Sun imaging pipelines

Quiet Sun, 3 December 2015, 03:39–03:44 UT, Sharma & Oberoi 2020 Figure 4
event. Three complete paths from the same visibilities:

1. **Sharma & Oberoi 2020** — published SuperUniform FITS, Haslam 1982 at
   this pointing, Mohan F(ν) at 5σ, time mean.
2. **CASA remake** — this work, CASA 6.6 tclean with the same SuperUniform
   numbers, the same flux method.
3. **P-AIRCARS** — Kansabanik et al., WSClean, flux from the calibrator
   sky model.

Kernel: `solar-burst-multiview`. Run from the top. Each section shows the
step and a picture.

Handover for the next agent: `docs/quiet-sun-handover.md`.
"""
    ),
    code(
        """\
from pathlib import Path
import sys
from IPython.display import Image, display

here = Path.cwd()
ROOT = here if (here / "src" / "solarburst").exists() else here.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
FIG = ROOT / "figures" / "pipelines"
from pipelines import paper_2020, casa_remake, paircars
"""
    ),
    md("## 1. The three columns"),
    md(
        """\
Grey is the published 2020 method. Blue is the CASA remake. Green is
P-AIRCARS. Each column runs calibration, imaging, flux scale, and product
on its own.
"""
    ),
    code(
        """\
from pipelines import diagram
diagram.main()
display(Image(filename=str(ROOT / "figures" / "pipelines.png"), width=980))
"""
    ),
    md("## 2. Sharma & Oberoi 2020 — published SuperUniform maps"),
    md(
        """\
### 2.1 Imaging settings from the FITS HISTORY

CASA 5.3 classic `clean`, SuperUniform, Hogbom, 8000 iterations. These
numbers are in the published FITS, not guessed.
"""
    ),
    code(
        """\
from pprint import pprint
path = paper_2020.one_frame("108")
print(path.name)
pprint(paper_2020.last_clean_from_history(path))
print("CLEAN dict")
pprint(paper_2020.CLEAN)
"""
    ),
    md(
        """\
### 2.2 One half-second map, Jy/beam

Frame `.0306` sits in the middle of the 03:39–03:44 UT scan.
"""
    ),
    code(
        """\
import matplotlib.pyplot as plt
from solarburst.maps import load_casa_2d

data, hdr = load_casa_2d(path)
print("shape", data.shape, "BUNIT", hdr.get("BUNIT"),
      "BMAJ", round(float(hdr["BMAJ"])*3600, 1), "arcsec",
      "DATE-OBS", hdr.get("DATE-OBS"))
fig, ax = plt.subplots(figsize=(4.2, 4.2))
im = ax.imshow(data, origin="lower", cmap="gray")
ax.set_title("Published 108 MHz, frame 0306, Jy/beam")
ax.set_xlabel("pixel"); ax.set_ylabel("pixel")
fig.colorbar(im, ax=ax, fraction=0.046)
plt.show()
"""
    ),
    md(
        """\
### 2.3 Whole-Sun flux and Mohan F(ν)

S_⊙ is the Oberoi 2017 integral with Haslam 1982 at this pointing.
F(ν) stretches the uncalibrated map so the radio Sun has that flux.
T_B follows from the restoring beam.
"""
    ),
    code(
        """\
sodot = paper_2020.s_odot_jy("108")
rec = paper_2020.scale_frame(path, sodot)
print(f"S_⊙ = {sodot/1e4:.3f} SFU")
print(f"F(ν) = {rec['f_nu']:.2f}")
print(f"off-Sun σ = {rec['sigma_jybeam']:.4f} Jy/beam")
print(f"mask pixels = {rec['n_mask']}")
print(f"peak T_B = {float(rec['tb_K'].max())/1e6:.3f} MK")
"""
    ),
    md("### 2.4 Time mean of 570 frames"),
    code(
        """\
paper_2020.demo()
display(Image(filename=str(FIG / "paper_2020_demo.png"), width=980))
mean = paper_2020.load_mean("108")
print(f"n = {mean['n']}  mean F(ν) = {mean['f_nu_mean']:.2f}  "
      f"peak = {float(mean['tb'].max())/1e6:.3f} MK")
"""
    ),
    md("## 3. CASA remake — SuperUniform on CASA 6.6"),
    md(
        """\
Same phase-only bandpass tables, same SuperUniform / Hogbom / 8000
numbers, same Haslam + Mohan conversion. Imaging ran on calculon
(`quiet_noon_casa_snap.py` / `sharma2020_casa_snap.py`). This notebook
reads the FITS that are already on the laptop.
"""
    ),
    code(
        """\
from pprint import pprint
pprint(casa_remake.IMAGING)
cpath = casa_remake.one_frame("108")
print(cpath.name, "frames on disk", len(casa_remake.list_frames("108")))
"""
    ),
    md("### 3.1 One half-second remake, then Mohan, then the mean"),
    code(
        """\
casa_remake.demo()
display(Image(filename=str(FIG / "casa_remake_demo.png"), width=980))
"""
    ),
    md("## 4. P-AIRCARS — separate column"),
    md(
        """\
Calibrator sky model, WSClean Briggs 0, solar north. Flux from the
calibrator. The cube for this event is one map over the scan at 4 s
native resolution. T_B on the right is Rayleigh–Jeans with that beam.
"""
    ),
    code(
        """\
from pprint import pprint
pprint(paircars.CLUSTER)
cube = paircars.load_cube(paircars.cube_path("84-85"))
print("data", cube["data"].shape, "freqs MHz", cube["freqs"], "extent", cube["extent"])
paircars.demo()
display(Image(filename=str(FIG / "paircars_demo.png"), width=720))
"""
    ),
    md("## 5. The three products at 108 MHz, side by side"),
    code(
        """\
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Circle

fig, axes = plt.subplots(1, 3, figsize=(13.2, 4.2), constrained_layout=True)
panels = [
    (paper_2020.load_mean("108"), "Sharma & Oberoi 2020", paper_2020.show_tb),
    (casa_remake.load_mean("108"), "CASA remake", casa_remake.show_tb),
]
p = paper_2020.load_mean("108")
paper_2020.show_tb(
    axes[0], p["tb"], p["extent"],
    (p["bmaj_deg"], p["bmin_deg"], p["bpa_deg"]),
    f"Published mean, n={p['n']}",
)
c = casa_remake.load_mean("108")
casa_remake.show_tb(
    axes[1], c["tb"], c["extent"],
    (c["bmaj_deg"], c["bmin_deg"], c["bpa_deg"]),
    f"CASA remake mean, n={c['n']}",
)
pc = paircars.tb_plane(paircars.load_cube(paircars.cube_path("84-85")), 108.0)
paircars.show_tb(
    axes[2], pc["tb_K"], pc["extent"],
    (pc["bmaj_arcsec"], pc["bmin_arcsec"], pc["bpa_deg"]),
    "P-AIRCARS, one map over the scan",
)
axes[0].set_ylabel("Solar Y (arcsec)", fontsize=8)
fig.suptitle("3 December 2015, 03:39–03:44 UT, 108 MHz. Solar north up on P-AIRCARS; "
             "published and CASA remake are still celestial north in this cell.",
             fontsize=10)
plt.show()
"""
    ),
    md(
        """\
## 6. Other quiet noon days (CASA remake already on disk)

Same CASA SuperUniform path as section 3.

| Day | Interval (UT) | Product |
|---|---|---|
| 3 December 2015 | 03:49–03:54 | published SuperUniform FITS (noon pick) |
| 4 December 2015 | 03:50–03:55 | CASA remake mean of 579 × 0.5 s |
| 8 December 2015 | 03:36–03:41 | CASA remake, Haslam at this pointing |
| 26 March 2015 | 03:46–03:51 | CASA remake frames; Mohan mean kept 38 / 583 / 225 / 2 frames at 108 / 162 / 217 / 240 MHz |

P-AIRCARS for 8 December 2015, 03:36–03:41 UT, 108 MHz is the job that was
running when this notebook was written. Continue that column next: 8
December remaining bands, then 4 December, then 3 December 03:49 with
`MEMFRAC=0.10`.
"""
    ),
]

nb = {
    "nbformat": 4,
    "nbformat_minor": 5,
    "metadata": {
        "kernelspec": {
            "display_name": "Python (solar-burst-multiview)",
            "language": "python",
            "name": "python3",
        }
    },
    "cells": cells,
}
OUT.write_text(json.dumps(nb, indent=1) + "\n")
print(f"wrote {OUT}")
