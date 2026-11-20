#!/usr/bin/env python3
"""Rohit's 162 MHz Figure 4 map beside P-AIRCARS at 145.9 MHz, one colour scale.

Rohit's CASA maps are RA/Dec (celestial north). P-AIRCARS writes HPLN/HPLT
(solar north). They differ by the solar P-angle. This figure keeps Rohit's
map as he plotted it and rotates P-AIRCARS by −P onto that frame.

    python scripts/fig4_vs_paircars_146.py
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("SUNPY_CONFIGDIR", tempfile.mkdtemp(prefix="sunpy-"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from astropy.time import Time
from matplotlib.patches import Circle, Ellipse
from scipy.ndimage import rotate
from sunpy.coordinates import sun

OUT = ROOT / "figures" / "quiet2015" / "fig4_162_vs_paircars.png"
OBS_TIME = Time("2015-12-03T03:42:04")
RSUN = 958.0
FOV = 2500.0
CUT_MK = 0.2
CONTOURS = (0.70, 0.75, 0.80, 0.85, 0.90, 0.95)
K_B, C = 1.380649e-23, 299792458.0


def p_angle_deg() -> float:
    return float(sun.P(OBS_TIME).to_value("deg"))


def rotate_map(tb: np.ndarray, angle_deg: float) -> np.ndarray:
    """Rotate a sun-centred map. Positive angle is counter-clockwise."""
    return rotate(
        np.nan_to_num(np.asarray(tb, dtype=np.float64), nan=0.0),
        angle_deg,
        reshape=False,
        order=1,
        cval=0.0,
    )


def paircars_tb(path: Path, chan: int = 1, rotate_deg: float = 0.0) -> dict:
    d = np.load(path)
    img = np.nanmean(d["data"][:, chan], axis=0)
    nu = float(d["freqs"][chan]) * 1e6
    bmaj, bmin = (float(x) for x in d["beams"][chan][:2])
    bpa = float(d["beams"][chan][2]) if len(d["beams"][chan]) > 2 else 0.0
    omega = np.pi * np.radians(bmaj / 3600.0) * np.radians(bmin / 3600.0) / (4 * np.log(2))
    tb_mk = img * 1e-26 * C**2 / (2 * K_B * nu**2 * omega) / 1e6
    if rotate_deg:
        tb_mk = rotate_map(tb_mk, rotate_deg)
    return {
        "tb": tb_mk,
        "extent": d["extent"],
        "beam_arcsec": (bmaj, bmin, bpa),
        "freq_mhz": nu / 1e6,
        "rotate_deg": rotate_deg,
    }


def rohit_162() -> dict:
    z = np.load(ROOT / "data" / "quiet2015" / "fig4_tb_perframe.npz")
    return {
        "tb": z["162_tb"] / 1e6,
        "extent": z["162_extent"],
        "beam_arcsec": (
            float(z["162_bmaj_deg"]) * 3600.0,
            float(z["162_bmin_deg"]) * 3600.0,
            float(z["162_bpa_deg"]),
        ),
        "freq_mhz": 162.0,
        "rotate_deg": 0.0,
    }


def show(ax, rec: dict, title: str, vmax: float, overlay: dict | None = None):
    tb = rec["tb"]
    peak = float(np.nanmax(tb))
    shown = np.where(tb > CUT_MK, tb, np.nan)
    im = ax.imshow(
        shown,
        origin="lower",
        extent=rec["extent"],
        cmap="jet",
        vmin=0.0,
        vmax=vmax,
        interpolation="nearest",
    )
    ax.contour(
        tb,
        levels=[f * peak for f in CONTOURS],
        extent=rec["extent"],
        origin="lower",
        colors="black",
        linewidths=0.7,
    )
    if overlay is not None:
        opk = float(np.nanmax(overlay["tb"]))
        ax.contour(
            overlay["tb"],
            levels=[0.50 * opk, 0.80 * opk],
            extent=overlay["extent"],
            origin="lower",
            colors="white",
            linewidths=1.0,
            linestyles=("dashed", "solid"),
        )
    for r in (1, 2):
        ax.add_patch(Circle((0, 0), r * RSUN, fill=False, color="brown", lw=1.6))
    bmaj, bmin, bpa = rec["beam_arcsec"]
    ax.add_patch(
        Ellipse(
            (-2000, -2000),
            bmin,
            bmaj,
            angle=-bpa + rec.get("rotate_deg", 0.0),
            fill=False,
            color="black",
            lw=1.1,
        )
    )
    ax.set_xlim(-FOV, FOV)
    ax.set_ylim(-FOV, FOV)
    ax.set_aspect("equal")
    ax.set_xlabel("Solar X (arcsec)")
    ax.set_title(title, fontsize=11)
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
    return im


def main() -> None:
    p_deg = p_angle_deg()
    # P-AIRCARS is solar north. Figure 4 is celestial north. −P puts P-AIRCARS
    # on Rohit's axes. Confirmed against radec_to_hpc on his CASA FITS.
    pc_to_rohit = -p_deg
    his = rohit_162()
    pc = paircars_tb(
        ROOT / "data" / "quiet2015" / "1133149192_ch113_quiet.npz", 1, pc_to_rohit
    )
    ns = paircars_tb(
        ROOT / "data" / "quiet2015" / "1133149192_ch113_noself.npz", 1, pc_to_rohit
    )
    panels = [
        (
            his,
            f"Rohit  ·  {his['freq_mhz']:.0f} MHz\nhis CASA maps (Figure 4)",
            None,
        ),
        (
            pc,
            f"P-AIRCARS  ·  {pc['freq_mhz']:.1f} MHz\nself-cal, onto Rohit's north",
            his,
        ),
        (
            ns,
            f"P-AIRCARS  ·  {ns['freq_mhz']:.1f} MHz\ncalibrator only, onto Rohit's north",
            his,
        ),
    ]
    vmax = 1.10
    fig, axes = plt.subplots(1, 3, figsize=(14.0, 5.2))
    last = None
    for i, (ax, (rec, title, overlay)) in enumerate(zip(axes, panels)):
        last = show(ax, rec, title, vmax, overlay)
        if i == 0:
            ax.set_ylabel("Solar Y (arcsec)")
        else:
            ax.set_yticklabels([])
    fig.subplots_adjust(left=0.06, right=0.90, top=0.82, bottom=0.16, wspace=0.08)
    cb = fig.colorbar(last, ax=axes, fraction=0.035, pad=0.02)
    cb.set_label("brightness temperature (million K)")
    fig.suptitle(
        "3 December 2015, observation 1133149192. Same colour scale (0–1.10 million K).",
        fontsize=12,
        y=0.98,
    )
    fig.text(
        0.48,
        0.02,
        f"Rohit's maps are celestial north; P-AIRCARS is solar north "
        f"(P = {p_deg:.1f}° that day). P-AIRCARS is rotated by {pc_to_rohit:+.1f}° "
        "onto Rohit's axes. White contours are Rohit's 50 % and 80 %.",
        ha="center",
        va="bottom",
        fontsize=9,
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=140)
    plt.close(fig)
    print(f"wrote {OUT}")
    print(f"P = {p_deg:.3f} deg; P-AIRCARS rotated by {pc_to_rohit:+.3f} deg")
    for rec, title, _ in panels:
        print(f"  peak {float(np.nanmax(rec['tb'])):.3f} MK   {title.split(chr(10))[0]}")


if __name__ == "__main__":
    main()
