#!/usr/bin/env python3
"""Rohit, our remake, and P-AIRCARS at the four Figure 4 frequencies, solar north.

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

OUT = ROOT / "figures" / "quiet2015" / "fig4_vs_paircars.png"
OBS_TIME = Time("2015-12-03T03:42:04")
RSUN = 958.0
FOV = 2500.0
CUT_MK = 0.2
CONTOURS = (0.70, 0.75, 0.80, 0.85, 0.90, 0.95)
K_B, C = 1.380649e-23, 299792458.0
# Paper label, npz prefix, P-AIRCARS pair, target MHz for choosing the cube plane.
BANDS = (
    ("108", "108", "84-85", 108.0),
    ("162", "162", "125-126", 162.0),
    ("217", "217", "169-170", 217.0),
    ("240", "240", "187-188", 240.0),
)


def p_angle_deg() -> float:
    return float(sun.P(OBS_TIME).to_value("deg"))


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


def paircars_tb(path: Path, target_mhz: float) -> dict:
    d = np.load(path)
    freqs = np.asarray(d["freqs"], dtype=np.float64)
    chan = int(np.argmin(np.abs(freqs - target_mhz)))
    img = np.nanmean(d["data"][:, chan], axis=0)
    nu = float(freqs[chan]) * 1e6
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
        "freq_mhz": float(prefix),
        "rotate_deg": rotate_deg,
        "n": int(z[f"{prefix}_n"]) if f"{prefix}_n" in z.files else 570,
    }


def show(ax, rec: dict, title: str, vmax: float, overlay: dict | None = None, *,
         ylabel: bool, xlabel: bool, coltitle: str | None):
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
        linewidths=0.6,
    )
    if overlay is not None:
        opk = float(np.nanmax(overlay["tb"]))
        ax.contour(
            overlay["tb"],
            levels=[0.50 * opk, 0.80 * opk],
            extent=overlay["extent"],
            origin="lower",
            colors="white",
            linewidths=0.9,
            linestyles=("dashed", "solid"),
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
    if xlabel:
        ax.set_xlabel("Solar X (arcsec)")
    else:
        ax.set_xticklabels([])
    if ylabel:
        ax.set_ylabel("Solar Y (arcsec)")
    else:
        ax.set_yticklabels([])
    if coltitle:
        ax.set_title(coltitle, fontsize=11)
    ax.text(
        0.03,
        0.97,
        f"{peak:.2f} MK",
        transform=ax.transAxes,
        va="top",
        fontsize=8,
        color="white",
        bbox=dict(boxstyle="round,pad=0.12", fc="black", alpha=0.45, lw=0),
    )
    return im


def main() -> None:
    p_deg = p_angle_deg()
    to_solar = p_deg
    data = ROOT / "data" / "quiet2015"
    rows = []
    for lab, prefix, pair, target in BANDS:
        his = casa_tb(data / "fig4_tb_perframe.npz", prefix, to_solar)
        ours = casa_tb(data / "fig4_ours_tb.npz", prefix, to_solar)
        pc = paircars_tb(data / f"1133149192_ch{pair}_quiet.npz", target)
        ns = paircars_tb(data / f"1133149192_ch{pair}_noself_noself.npz", target)
        rows.append((lab, his, ours, pc, ns))

    peaks = [
        float(np.nanmax(rec["tb"]))
        for _, his, ours, pc, ns in rows
        for rec in (his, ours, pc, ns)
    ]
    vmax = 1.10
    if max(peaks) > vmax:
        vmax = float(np.ceil(max(peaks) * 10.0) / 10.0)

    fig, axes = plt.subplots(4, 4, figsize=(14.8, 14.2))
    coltitles = (
        "Rohit\nhis CASA maps (Figure 4)",
        "Ours\nSuperUniform remake, 570 × 0.5 s",
        "P-AIRCARS\nself-cal, one map over the scan",
        "P-AIRCARS\ncalibrator only, one map over the scan",
    )
    last = None
    for i, (lab, his, ours, pc, ns) in enumerate(rows):
        recs = (his, ours, pc, ns)
        for j, rec in enumerate(recs):
            overlay = his if j > 0 else None
            last = show(
                axes[i, j],
                rec,
                "",
                vmax,
                overlay,
                ylabel=(j == 0),
                xlabel=(i == 3),
                coltitle=coltitles[j] if i == 0 else None,
            )
        axes[i, 0].text(
            -0.32,
            0.5,
            f"{lab} MHz",
            transform=axes[i, 0].transAxes,
            rotation=90,
            va="center",
            ha="center",
            fontsize=12,
        )
    fig.subplots_adjust(left=0.10, right=0.90, top=0.90, bottom=0.08, wspace=0.04, hspace=0.08)
    cb = fig.colorbar(last, ax=axes, fraction=0.025, pad=0.02)
    cb.set_label("brightness temperature (million K)")
    fig.suptitle(
        "3 December 2015, observation 1133149192. Solar north up. "
        f"Same colour scale (0–{vmax:.2f} million K).",
        fontsize=13,
        y=0.98,
    )
    fig.text(
        0.50,
        0.012,
        f"Rohit and our remake were celestial north; both are rotated by "
        f"+{p_deg:.1f}° (the P-angle that day) onto solar north. "
        "P-AIRCARS is already solar north. White contours are Rohit's 50 % and 80 %. "
        "At 217 and 240 MHz P-AIRCARS did not recover the disk.",
        ha="center",
        va="bottom",
        fontsize=9,
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=130)
    plt.close(fig)
    print(f"wrote {OUT}")
    print(f"P = {p_deg:.3f} deg; vmax = {vmax:.2f} million K")
    for lab, his, ours, pc, ns in rows:
        print(
            f"  {lab} MHz  Rohit {np.nanmax(his['tb']):.3f}  "
            f"ours {np.nanmax(ours['tb']):.3f}  "
            f"P-AIRCARS {np.nanmax(pc['tb']):.3f} ({pc['freq_mhz']:.1f} MHz)  "
            f"noself {np.nanmax(ns['tb']):.3f} ({ns['freq_mhz']:.1f} MHz)"
        )


if __name__ == "__main__":
    main()
