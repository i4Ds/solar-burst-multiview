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


def tb_map(cube: Path, chan: int, quantile: float):
    d = np.load(cube)
    imgs = d["data"][:, chan]
    nu = float(d["freqs"][chan]) * 1e6
    bmaj, bmin = (float(x) for x in d["beams"][chan][:2])
    bpa = float(d["beams"][chan][2]) if len(d["beams"][chan]) > 2 else 0.0
    peaks = np.array([np.nanmax(im) for im in imgs])
    qmap = np.nanmean(imgs[peaks <= np.quantile(peaks, quantile)], axis=0)
    omega = np.pi * np.radians(bmaj / 3600) * np.radians(bmin / 3600) / (4 * np.log(2))
    tb = qmap * 1e-26 * C**2 / (2 * K_B * nu**2 * omega) / 1e6
    return tb, d["extent"], nu, (bmaj, bmin, bpa)


def draw(ax, tb, ext, beam, title, vmax, cut, contours=True):
    bmaj, bmin, bpa = beam
    im = ax.imshow(np.where(tb > cut, tb, np.nan), origin="lower", extent=ext, cmap="jet", vmin=0, vmax=vmax,
                   interpolation="nearest")
    peak = np.nanmax(tb)
    if contours:
        ax.contour(tb, levels=[f * peak for f in (0.70, 0.75, 0.80, 0.85, 0.90, 0.95)], extent=ext,
                   origin="lower", colors="black", linewidths=0.8)
    for r in (1, 2):
        ax.add_patch(Circle((0, 0), r * RSUN, fill=False, color="brown", lw=2))
    ax.add_patch(Ellipse((-2000, -2000), bmin, bmaj, angle=-bpa, fill=False, color="black", lw=1.2))
    ax.set_xlim(-2500, 2500); ax.set_ylim(-2500, 2500); ax.set_aspect("equal")
    ax.grid(ls=":", color="grey", lw=0.6)
    ax.set_xlabel("Solar X (arcsec)", fontsize=12); ax.set_ylabel("Solar Y (arcsec)", fontsize=12)
    ax.set_title(title, fontsize=12)
    ax.text(0.02, 0.98, f"peak {peak:.2f} MK", transform=ax.transAxes, va="top", fontsize=9)
    return im, peak


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("cube", type=Path, nargs="+", help="one or more cubes, drawn side by side")
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--title", action="append", default=[], help="one per cube")
    p.add_argument("--chan", type=int, action="append", default=[], help="frequency index, one per cube (default 0)")
    p.add_argument("--quantile", type=float, default=1.0)
    p.add_argument("--vmax", type=float, default=1.5, help="MK")
    p.add_argument("--cut", type=float, default=0.2, help="MK; lower values are not shown")
    p.add_argument("--no-contours", action="store_true", help="omit the 70-95 %% of peak contours")
    p.add_argument("--suptitle", default="")
    a = p.parse_args()

    n = len(a.cube)
    fig, axs = plt.subplots(1, n, figsize=(6.4 * n + 1, 5.6), layout="constrained", squeeze=False)
    for k, (ax, cube) in enumerate(zip(axs[0], a.cube)):
        chan = a.chan[k] if k < len(a.chan) else 0
        tb, ext, nu, beam = tb_map(cube, chan, a.quantile)
        title = a.title[k] if k < len(a.title) else f"{nu/1e6:.0f} MHz"
        im, peak = draw(ax, tb, ext, beam, title, a.vmax, a.cut, not a.no_contours)
        print(f"{cube} ch{chan}: peak {peak:.2f} MK, median(T_B>{a.cut}) {np.nanmedian(tb[tb > a.cut]):.2f} MK, "
              f"beam {beam[0]:.0f}\" x {beam[1]:.0f}\"")
    fig.colorbar(im, ax=axs[0, -1], pad=0.02).set_label("(MK)", fontsize=13)
    if a.suptitle:
        fig.suptitle(a.suptitle, fontsize=13)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(f"{a.out}.png", dpi=130, bbox_inches="tight")
    print(f"wrote {a.out}.png")


if __name__ == "__main__":
    main()
