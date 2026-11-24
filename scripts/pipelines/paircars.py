#!/usr/bin/env python3
"""P-AIRCARS quiet-Sun column.

Calibration: compact-calibrator sky model, then optional intensity
self-calibration (Mondal et al. 2019). Imaging: WSClean, Briggs robust 0,
helioprojective, solar north. Flux: the calibrator model; maps are
primary-beam-corrected Jy/beam. Brightness temperature for plots is
Rayleigh–Jeans with the restoring beam in the cube.

This file reads cubes already written on calculon. Launch is
scripts/calculon/overnight/burst_series.sh with TAG, TRANGE, TRES, CALDIR.

    python scripts/pipelines/paircars.py --demo

Figure 4 event cubes: data/quiet2015/1133149192_ch{84-85,125-126,169-170,187-188}_quiet.npz
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from astropy import constants as const
from matplotlib.patches import Circle, Ellipse

from solarburst.config import REPO_ROOT
from solarburst.maps import beam_solid_angle_sr

CUBES = REPO_ROOT / "data" / "quiet2015"
OUTDIR = REPO_ROOT / "figures" / "pipelines"
RSUN, FOV = 958.0, 2500.0
CONTOURS = (0.70, 0.75, 0.80, 0.85, 0.90, 0.95)

BANDS = (
    ("108", "84-85", 108.0),
    ("162", "125-126", 162.0),
    ("217", "169-170", 217.0),
    ("240", "187-188", 240.0),
)
OBS_TIME = "3 December 2015, 03:39–03:44 UT"

# Cluster launch for this event (4 s Sun, 3C444, one map over the scan).
CLUSTER = {
    "sun": "1133149192",
    "cal": "1133161488",
    "trange": "2015/12/03/03:39:44~2015/12/03/03:44:24",
    "tres": 280,
    "script": "scripts/calculon/overnight/fig4_paircars_bands.sh",
    "watcher": "scripts/calculon/overnight/burst_series.sh",
}


def cube_path(pair: str, *, selfcal: bool = True) -> Path:
    tag = "quiet" if selfcal else "noself_noself"
    return CUBES / f"1133149192_ch{pair}_{tag}.npz"


def load_cube(path: Path) -> dict:
    z = np.load(path)
    return {
        "data": np.asarray(z["data"], dtype=np.float64),
        "times": np.asarray(z["times"]),
        "freqs": np.asarray(z["freqs"], dtype=np.float64),
        "beams": np.asarray(z["beams"], dtype=np.float64),
        "extent": np.asarray(z["extent"], dtype=np.float64),
    }


def tb_plane(cube: dict, target_mhz: float) -> dict:
    """Time-mean Stokes I at the nearest channel, Jy/beam and MK."""
    chan = int(np.argmin(np.abs(cube["freqs"] - target_mhz)))
    img = np.nanmean(cube["data"][:, chan], axis=0)
    nu = float(cube["freqs"][chan]) * 1e6
    bmaj, bmin = (float(x) for x in cube["beams"][chan][:2])
    bpa = float(cube["beams"][chan][2]) if cube["beams"].shape[1] > 2 else 0.0
    omega = beam_solid_angle_sr(bmaj / 3600.0, bmin / 3600.0)
    tb_k = img * 1e-26 * const.c.value**2 / (2.0 * const.k_B.value * nu**2 * omega)
    return {
        "jybeam": img,
        "tb_K": tb_k,
        "extent": cube["extent"],
        "bmaj_arcsec": bmaj,
        "bmin_arcsec": bmin,
        "bpa_deg": bpa,
        "freq_mhz": nu / 1e6,
        "n_time": int(cube["data"].shape[0]),
        "n_chan": int(cube["data"].shape[1]),
    }


def show_tb(ax, tb_k, extent, beam_arcsec, title: str) -> float:
    tb = np.asarray(tb_k, dtype=np.float64) / 1e6
    peak = float(np.nanmax(tb))
    cut = 0.12 * peak if peak > 0 else 0.0
    shown = np.where(tb > cut, tb, np.nan)
    ax.imshow(
        shown,
        origin="lower",
        extent=extent,
        cmap="jet",
        vmin=0.0,
        vmax=max(peak, 1e-6),
        interpolation="nearest",
    )
    if peak > 0:
        ax.contour(
            tb,
            levels=[f * peak for f in CONTOURS],
            extent=extent,
            origin="lower",
            colors="black",
            linewidths=0.6,
        )
    for r in (1, 2):
        ax.add_patch(Circle((0, 0), r * RSUN, fill=False, color="brown", lw=1.3))
    bmaj, bmin, bpa = beam_arcsec
    ax.add_patch(
        Ellipse((-2000, -2000), bmin, bmaj, angle=-bpa, fill=False, color="black", lw=1.0)
    )
    ax.set_xlim(-FOV, FOV)
    ax.set_ylim(-FOV, FOV)
    ax.set_aspect("equal")
    ax.set_title(title, fontsize=11)
    ax.set_xlabel("Solar X (arcsec)", fontsize=8)
    ax.tick_params(labelsize=8)
    ax.text(
        0.03,
        0.97,
        f"{peak:.2f} MK",
        transform=ax.transAxes,
        va="top",
        fontsize=9,
        color="white",
        bbox=dict(boxstyle="round,pad=0.15", fc="black", alpha=0.45, lw=0),
    )
    return peak


def demo(out: Path | None = None) -> Path:
    lab, pair, mhz = BANDS[0]
    cube = load_cube(cube_path(pair, selfcal=True))
    rec = tb_plane(cube, mhz)
    out = out or OUTDIR / "paircars_demo.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 4.0), constrained_layout=True)
    axes[0].imshow(rec["jybeam"], origin="lower", extent=rec["extent"], cmap="gray")
    axes[0].set_title("P-AIRCARS Stokes I, Jy/beam")
    axes[0].set_xlabel("Solar X (arcsec)", fontsize=8)
    axes[0].set_ylabel("Solar Y (arcsec)", fontsize=8)
    axes[0].set_xlim(-FOV, FOV)
    axes[0].set_ylim(-FOV, FOV)
    axes[0].set_aspect("equal")
    show_tb(
        axes[1],
        rec["tb_K"],
        rec["extent"],
        (rec["bmaj_arcsec"], rec["bmin_arcsec"], rec["bpa_deg"]),
        f"Rayleigh–Jeans  {rec['freq_mhz']:.1f} MHz",
    )
    fig.suptitle(
        f"P-AIRCARS  ·  {OBS_TIME}  ·  {lab} MHz  ·  self-cal  ·  "
        f"{rec['n_time']} time  ×  {rec['n_chan']} chan",
        fontsize=11,
    )
    fig.savefig(out, dpi=140, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {out}")
    print(
        f"peak {float(np.nanmax(rec['tb_K']))/1e6:.3f} MK  "
        f"beam {rec['bmaj_arcsec']:.0f}″×{rec['bmin_arcsec']:.0f}″"
    )
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--demo", action="store_true")
    args = p.parse_args(argv)
    print("P-AIRCARS cluster launch:")
    for k, v in CLUSTER.items():
        print(f"  {k:12s} {v}")
    demo()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
