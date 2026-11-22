#!/usr/bin/env python3
"""4 December 2015 quiet-Sun mean maps, solar north, next to Figure 4.

    python scripts/dec4_quiet_maps.py
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

OUTDIR = ROOT / "figures" / "quiet2015"
DEC4 = ROOT / "data" / "quiet2015" / "dec4"
FIG4 = ROOT / "data" / "quiet2015" / "fig4_ours_tb.npz"
BANDS = ("108", "162", "217", "240")
RSUN = 958.0
FOV = 2500.0
CONTOURS = (0.70, 0.75, 0.80, 0.85, 0.90, 0.95)


def p_angle(iso: str) -> float:
    return float(sun.P(Time(iso)).to_value("deg"))


def rotate_map(tb: np.ndarray, angle_deg: float) -> np.ndarray:
    if not angle_deg:
        return np.asarray(tb, dtype=np.float64)
    return rotate(
        np.nan_to_num(np.asarray(tb, dtype=np.float64), nan=0.0),
        angle_deg,
        reshape=False,
        order=1,
        cval=0.0,
    )


def load_dec4(lab: str, rotate_deg: float) -> dict:
    z = np.load(DEC4 / f"{lab}MHz_tb.npz")
    return {
        "tb": rotate_map(z["tb"] / 1e6, rotate_deg),
        "extent": z["extent"],
        "beam_arcsec": (float(z["bmaj_deg"]) * 3600.0, float(z["bmin_deg"]) * 3600.0, float(z["bpa_deg"])),
        "n": int(z["n"]),
        "f_nu": float(z["f_nu_mean"]),
        "sfu": float(z["s_odot_jy"]) / 1e4,
        "rotate_deg": rotate_deg,
    }


def load_fig4(lab: str, rotate_deg: float) -> dict:
    z = np.load(FIG4)
    return {
        "tb": rotate_map(z[f"{lab}_tb"] / 1e6, rotate_deg),
        "extent": z[f"{lab}_extent"],
        "beam_arcsec": (
            float(z[f"{lab}_bmaj_deg"]) * 3600.0,
            float(z[f"{lab}_bmin_deg"]) * 3600.0,
            float(z[f"{lab}_bpa_deg"]),
        ),
        "n": int(z[f"{lab}_n"]),
        "rotate_deg": rotate_deg,
    }


def show(ax, rec: dict, title: str, *, ylabel: bool, xlabel: bool):
    tb = rec["tb"]
    peak = float(np.nanmax(tb))
    cut = 0.12 * peak if peak > 0 else 0.0
    shown = np.where(tb > cut, tb, np.nan)
    im = ax.imshow(
        shown,
        origin="lower",
        extent=rec["extent"],
        cmap="jet",
        vmin=0.0,
        vmax=max(peak, 1e-6),
        interpolation="nearest",
    )
    if peak > 0:
        ax.contour(
            tb,
            levels=[f * peak for f in CONTOURS],
            extent=rec["extent"],
            origin="lower",
            colors="black",
            linewidths=0.6,
        )
    for r in (1, 2):
        ax.add_patch(Circle((0, 0), r * RSUN, fill=False, color="brown", lw=1.3))
    bmaj, bmin, bpa = rec["beam_arcsec"]
    ax.add_patch(
        Ellipse(
            (-2000, -2000),
            bmin,
            bmaj,
            angle=-bpa + rec.get("rotate_deg", 0.0),
            fill=False,
            color="black",
            lw=1.0,
        )
    )
    ax.set_xlim(-FOV, FOV)
    ax.set_ylim(-FOV, FOV)
    ax.set_aspect("equal")
    ax.set_title(title, fontsize=11)
    if xlabel:
        ax.set_xlabel("Solar X (arcsec)", fontsize=8)
    else:
        ax.set_xticklabels([])
    if ylabel:
        ax.set_ylabel("Solar Y (arcsec)", fontsize=8)
    else:
        ax.set_yticklabels([])
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
    return im, peak


def save(fig, name: str) -> Path:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    path = OUTDIR / name
    fig.savefig(path, dpi=140, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {path}", flush=True)
    return path


def main() -> None:
    p3 = p_angle("2015-12-03T03:42:04")
    p4 = p_angle("2015-12-04T03:52:00")
    dec4 = {lab: load_dec4(lab, p4) for lab in BANDS}
    fig4 = {lab: load_fig4(lab, p3) for lab in BANDS}

    fig, axes = plt.subplots(1, 4, figsize=(14.8, 3.9), constrained_layout=True)
    peaks = []
    for ax, lab in zip(axes, BANDS):
        _, pk = show(ax, dec4[lab], f"{lab} MHz", ylabel=(ax is axes[0]), xlabel=True)
        peaks.append(pk)
    fig.suptitle(
        "4 December 2015 · 1133236216 · CASA SuperUniform, mean of 579 × 0.5 s. "
        "Each panel scaled to its own peak. Solar north up.",
        fontsize=12,
    )
    save(fig, "dec4_ours_mean.png")
    print("dec4 peaks MK", [round(x, 3) for x in peaks])
    print("dec4 SFU", [round(dec4[lab]["sfu"], 3) for lab in BANDS])
    print("dec4 F(ν)", [round(dec4[lab]["f_nu"], 2) for lab in BANDS])
    print(f"P 3 Dec {p3:.3f} deg; P 4 Dec {p4:.3f} deg")

    fig, axes = plt.subplots(2, 4, figsize=(14.8, 7.6), constrained_layout=True)
    for j, lab in enumerate(BANDS):
        show(axes[0, j], fig4[lab], f"3 Dec  {lab} MHz", ylabel=(j == 0), xlabel=False)
        show(axes[1, j], dec4[lab], f"4 Dec  {lab} MHz", ylabel=(j == 0), xlabel=True)
    fig.suptitle(
        "Each panel scaled to its own peak. Solar north up. "
        "3 December is Figure 4 remake (Haslam at that pointing). "
        "4 December uses Oberoi 2017 Table 1 (2013 pointing).",
        fontsize=11,
    )
    save(fig, "fig4_vs_dec4.png")


if __name__ == "__main__":
    main()
