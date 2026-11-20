#!/usr/bin/env python3
"""Rohit, our remake, and P-AIRCARS of the 2015 quiet scan, all solar north.

Rohit's CASA maps and our SuperUniform remake are RA/Dec (celestial north).
P-AIRCARS writes HPLN/HPLT (solar north). They differ by the solar P-angle.
This figure rotates Rohit and our remake by +P onto solar north and leaves
P-AIRCARS as written.

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
    if not angle_deg:
        return np.asarray(tb, dtype=np.float64)
    return rotate(
        np.nan_to_num(np.asarray(tb, dtype=np.float64), nan=0.0),
        angle_deg,
        reshape=False,
        order=1,
        cval=0.0,
    )


def paircars_tb(path: Path, chan: int = 1) -> dict:
    d = np.load(path)
    img = np.nanmean(d["data"][:, chan], axis=0)
    nu = float(d["freqs"][chan]) * 1e6
    bmaj, bmin = (float(x) for x in d["beams"][chan][:2])
    bpa = float(d["beams"][chan][2]) if len(d["beams"][chan]) > 2 else 0.0
    omega = np.pi * np.radians(bmaj / 3600.0) * np.radians(bmin / 3600.0) / (4 * np.log(2))
    tb_mk = img * 1e-26 * C**2 / (2 * K_B * nu**2 * omega) / 1e6
    return {
        "tb": tb_mk,
        "extent": d["extent"],
        "beam_arcsec": (bmaj, bmin, bpa),
        "freq_mhz": nu / 1e6,
        "rotate_deg": 0.0,
    }


def casa_tb(path: Path, prefix: str, rotate_deg: float) -> dict:
    z = np.load(path)
    bmaj = float(z[f"{prefix}_bmaj_deg"])
    bmin = float(z[f"{prefix}_bmin_deg"])
    bpa = float(z[f"{prefix}_bpa_deg"])
    return {
        "tb": rotate_map(z[f"{prefix}_tb"] / 1e6, rotate_deg),
        "extent": z[f"{prefix}_extent"],
        "beam_arcsec": (bmaj * 3600.0, bmin * 3600.0, bpa),
        "freq_mhz": 162.0,
        "rotate_deg": rotate_deg,
        "n": int(z[f"{prefix}_n"]) if f"{prefix}_n" in z.files else 570,
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
    # Celestial north → solar north. Sign checked against radec_to_hpc.
    to_solar = p_deg
    his = casa_tb(ROOT / "data" / "quiet2015" / "fig4_tb_perframe.npz", "162", to_solar)
    ours = casa_tb(ROOT / "data" / "quiet2015" / "fig4_ours_tb.npz", "162", to_solar)
    pc = paircars_tb(ROOT / "data" / "quiet2015" / "1133149192_ch113_quiet.npz", 1)
    ns = paircars_tb(ROOT / "data" / "quiet2015" / "1133149192_ch113_noself.npz", 1)
    panels = [
        (
            his,
            f"Rohit  ·  {his['freq_mhz']:.0f} MHz\nhis CASA maps (Figure 4)",
            None,
        ),
        (
            ours,
            f"Ours  ·  {ours['freq_mhz']:.0f} MHz\n"
            f"SuperUniform remake, {ours['n']} × 0.5 s",
            his,
        ),
        (
            pc,
            f"P-AIRCARS  ·  {pc['freq_mhz']:.1f} MHz\nself-cal, one map over the scan",
            his,
        ),
        (
            ns,
            f"P-AIRCARS  ·  {ns['freq_mhz']:.1f} MHz\ncalibrator only, one map over the scan",
            his,
        ),
    ]
    vmax = 1.10
    fig, axes = plt.subplots(1, 4, figsize=(18.2, 5.2))
    last = None
    for i, (ax, (rec, title, overlay)) in enumerate(zip(axes, panels)):
        last = show(ax, rec, title, vmax, overlay)
        if i == 0:
            ax.set_ylabel("Solar Y (arcsec)")
        else:
            ax.set_yticklabels([])
    fig.subplots_adjust(left=0.045, right=0.93, top=0.82, bottom=0.16, wspace=0.06)
    cb = fig.colorbar(last, ax=axes, fraction=0.025, pad=0.015)
    cb.set_label("brightness temperature (million K)")
    fig.suptitle(
        "3 December 2015, observation 1133149192. "
        "Solar north up. Same colour scale (0–1.10 million K).",
        fontsize=12,
        y=0.98,
    )
    fig.text(
        0.48,
        0.02,
        f"Rohit and our remake were celestial north; both are rotated by "
        f"+{p_deg:.1f}° (the P-angle that day) onto solar north. "
        "P-AIRCARS is already solar north. White contours are Rohit's 50 % and 80 %.",
        ha="center",
        va="bottom",
        fontsize=9,
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=140)
    plt.close(fig)
    print(f"wrote {OUT}")
    print(f"P = {p_deg:.3f} deg; CASA maps rotated by {to_solar:+.3f} deg to solar north")
    for rec, title, _ in panels:
        print(f"  peak {float(np.nanmax(rec['tb'])):.3f} MK   {title.split(chr(10))[0]}")


if __name__ == "__main__":
    main()
