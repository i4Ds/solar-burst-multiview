"""One PNG of a P-AIRCARS image time series (cube from make_cube.py): every time
step for one frequency on a common colour scale, plus the peak brightness vs time.

    python3 montage.py CUBE.npz OUT.png [--freq 148.47] [--half 1500]
"""

import argparse

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle

RSUN = 958.0


def main():
    p = argparse.ArgumentParser()
    p.add_argument("cube")
    p.add_argument("out")
    p.add_argument("--freq", type=float, default=None)
    p.add_argument("--half", type=float, default=1500.0)
    a = p.parse_args()
    d = np.load(a.cube)
    cube, freqs, times, ext = d["data"], d["freqs"], d["times"], d["extent"]
    k = 0 if a.freq is None else int(np.argmin(np.abs(freqs - a.freq)))
    imgs = cube[:, k]
    vmax = np.nanmax(imgs)
    n = len(times)
    ncol = 5
    nrow = int(np.ceil(n / ncol)) + 1
    fig = plt.figure(figsize=(3.2 * ncol, 3.2 * nrow))
    for i, t in enumerate(times):
        ax = fig.add_subplot(nrow, ncol, i + 1)
        ax.imshow(imgs[i], origin="lower", extent=ext, cmap="inferno", vmin=0, vmax=vmax)
        ax.add_patch(Circle((0, 0), RSUN, fill=False, color="w", lw=0.6, ls="--"))
        ax.set_xlim(-a.half, a.half); ax.set_ylim(-a.half, a.half)
        ax.set_title(f"{t[8:10]}:{t[10:12]}:{t[12:]} UTC", fontsize=9)
        ax.tick_params(labelsize=7)
    ax = fig.add_subplot(nrow, 1, nrow)
    peaks = [np.nanmax(im) for im in imgs]
    ax.plot(range(n), peaks, "o-")
    ax.set_xticks(range(n)); ax.set_xticklabels([f"{t[10:12]}:{t[12:14]}" for t in times], fontsize=8)
    ax.set_ylabel("peak [Jy/beam]"); ax.set_xlabel("04:MM:SS (4 s steps)")
    fig.suptitle(f"P-AIRCARS {freqs[k]:.2f} MHz, Stokes I, 4 s, common scale (max {vmax:.3g} Jy/beam); solar north up, arcsec")
    fig.tight_layout()
    fig.savefig(a.out, dpi=100)
    print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
