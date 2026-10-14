"""Quiet-Sun T_B map in the style of Sharma & Oberoi (2020, ApJ 903, 126; arXiv:2009.10604), Fig. 4 top.

    python scripts/tb_map_sharma_style.py data/quiet2015/1133149192_ch113_quiet.npz \
        --title "145 MHz, 2015-12-03 03:39-03:44" --out figures/quiet2015/tb_1133149192_ch113

Linear T_B scale 0-1.5 MK (jet), only T_B > 0.2 MK shown, circles at 1 and 2 R_sun,
contours at 70, 75, 80, 85, 90 and 95 % of the peak, restoring beam in the lower left.
T_B from Rayleigh-Jeans with the restoring beam. Frames whose peak is at or below the
--quantile of all frame peaks are averaged (one frame: that frame).
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle, Ellipse

K_B, C = 1.380649e-23, 299792458.0
RSUN = 958.0  # arcsec; the paper's circles are drawn at the optical radius


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("cube", type=Path)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--title", default="")
    p.add_argument("--quantile", type=float, default=1.0)
    p.add_argument("--chan", type=int, default=0, help="frequency index in the cube")
    p.add_argument("--vmax", type=float, default=1.5, help="MK")
    p.add_argument("--cut", type=float, default=0.2, help="MK; lower values are not shown")
    a = p.parse_args()

    d = np.load(a.cube)
    imgs = d["data"][:, a.chan]
    nu = float(d["freqs"][a.chan]) * 1e6
    bmaj, bmin = (float(x) for x in d["beams"][a.chan][:2])
    bpa = float(d["beams"][a.chan][2]) if len(d["beams"][a.chan]) > 2 else 0.0
    peaks = np.array([np.nanmax(im) for im in imgs])
    qmap = np.nanmean(imgs[peaks <= np.quantile(peaks, a.quantile)], axis=0)
    omega = np.pi * np.radians(bmaj / 3600) * np.radians(bmin / 3600) / (4 * np.log(2))
    tb = qmap * 1e-26 * C**2 / (2 * K_B * nu**2 * omega) / 1e6
    ext = d["extent"]

    fig, ax = plt.subplots(figsize=(7.2, 5.6))
    shown = np.where(tb > a.cut, tb, np.nan)
    im = ax.imshow(shown, origin="lower", extent=ext, cmap="jet", vmin=0, vmax=a.vmax, interpolation="nearest")
    peak = np.nanmax(tb)
    ax.contour(tb, levels=[f * peak for f in (0.70, 0.75, 0.80, 0.85, 0.90, 0.95)], extent=ext,
               origin="lower", colors="black", linewidths=0.8)
    for r in (1, 2):
        ax.add_patch(Circle((0, 0), r * RSUN, fill=False, color="brown", lw=2))
    ax.add_patch(Ellipse((-2000, -2000), bmin, bmaj, angle=-bpa, fill=False, color="black", lw=1.2))
    cb = fig.colorbar(im, ax=ax, pad=0.02)
    cb.set_label("(MK)", fontsize=13)
    ax.set_xlim(-2500, 2500); ax.set_ylim(-2500, 2500); ax.set_aspect("equal")
    ax.grid(ls=":", color="grey", lw=0.6)
    ax.set_xlabel("Solar X (arcsec)", fontsize=13); ax.set_ylabel("Solar Y (arcsec)", fontsize=13)
    ax.set_title(a.title or f"{nu/1e6:.0f} MHz", fontsize=13)
    ax.text(0.02, 0.98, f"peak {peak:.2f} MK", transform=ax.transAxes, va="top", fontsize=9)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(f"{a.out}.png", dpi=130, bbox_inches="tight")
    print(f"wrote {a.out}.png  peak {peak:.2f} MK, median(T_B>{a.cut}) {np.nanmedian(shown):.2f} MK, "
          f"beam {bmaj:.0f}\" x {bmin:.0f}\" pa {bpa:.0f}")


if __name__ == "__main__":
    main()
