"""MWA burst time series as contours on AIA: one overlay PNG at the peak and a movie.

    python scripts/burst_movie.py data/flare20220930/overnight/burst10_ch116.npz \
        data/flare20220930/aia/aia.lev1.193A_2022_09_30T04_28_40.84Z.image_lev1.fits \
        --out figures/flare20220930/burst10_ch116_aia --zoom 300 120 600 --mark AR13110:240:158

The cube comes from scripts/calculon/overnight/make_cube.py (P-AIRCARS HPC images,
Stokes I). Contours are fractions of the maximum over all frames, so the burst
visibly rises and fades. The AIA image is the same in every frame. Writes
<out>_peak.png, <out>.gif and, if ffmpeg is available, <out>.mp4.
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

import astropy.units as u
import matplotlib.pyplot as plt
import numpy as np
from astropy.visualization import AsinhStretch, ImageNormalize
from matplotlib.animation import FFMpegWriter, FuncAnimation, PillowWriter
from matplotlib.patches import Circle
from sunpy.map import Map

from solarburst.maps import aia_hpc_cutout

LEVELS = (0.1, 0.3, 0.5, 0.7, 0.9)
RSUN = 958.0


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("cube", type=Path)
    p.add_argument("aia", type=Path)
    p.add_argument("--out", type=Path, required=True, help="output prefix")
    p.add_argument("--freq", type=float, default=None, help="MHz; default the first plane")
    p.add_argument("--zoom", nargs=3, type=float, default=(300, 120, 600), metavar=("X", "Y", "HALF"))
    p.add_argument("--fov", type=float, default=1300.0)
    p.add_argument("--mark", action="append", default=[], metavar="LABEL:X:Y")
    p.add_argument("--fps", type=float, default=2.0)
    a = p.parse_args()

    d = np.load(a.cube)
    cube, freqs, times, ext = d["data"], d["freqs"], d["times"], d["extent"]
    k = 0 if a.freq is None else int(np.argmin(np.abs(freqs - a.freq)))
    imgs = cube[:, k]
    gmax = np.nanmax(imgs)
    peaks = np.array([np.nanmax(im) for im in imgs])
    labels = [f"{t[8:10]}:{t[10:12]}:{t[12:14]}" for t in times]
    secs = [int(t[8:10]) * 3600 + int(t[10:12]) * 60 + float(t[12:]) for t in times]
    step = float(np.median(np.diff(secs))) if len(secs) > 1 else 0.0

    smap = Map(str(a.aia))
    aia, aext = aia_hpc_cutout(a.aia, fov_arcsec=a.fov)
    aia = aia / smap.exposure_time.to_value(u.s)
    wav = int(smap.wavelength.value)
    x, y, half = a.zoom
    zwin = (x - half, x + half, y - half, y + half)

    def norm_for(win):
        ny, nx = aia.shape
        cols = ((np.array(win[:2]) - aext[0]) / (aext[1] - aext[0]) * nx).astype(int).clip(0, nx)
        rows = ((np.array(win[2:]) - aext[2]) / (aext[3] - aext[2]) * ny).astype(int).clip(0, ny)
        vmax = np.nanpercentile(aia[rows[0]:rows[1], cols[0]:cols[1]], 99.9)
        return ImageNormalize(vmin=0, vmax=vmax, stretch=AsinhStretch(0.02))

    fig = plt.figure(figsize=(12, 7.6))
    gs = fig.add_gridspec(2, 2, height_ratios=[4, 1.1])
    ax_full, ax_zoom, ax_lc = fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[0, 1]), fig.add_subplot(gs[1, :])
    for ax, win in ((ax_full, (-a.fov, a.fov, -a.fov, a.fov)), (ax_zoom, zwin)):
        ax.imshow(aia, origin="lower", extent=aext, cmap=f"sdoaia{wav}", norm=norm_for(win))
        ax.add_patch(Circle((0, 0), RSUN, fill=False, color="white", lw=0.6, ls="--"))
        ax.set_xlim(win[0], win[1]); ax.set_ylim(win[2], win[3]); ax.set_aspect("equal")
        ax.set_xlabel("Solar X [arcsec]"); ax.set_ylabel("Solar Y [arcsec]")
        for mark in a.mark:
            lab, mx, my = mark.rsplit(":", 2)
            ax.plot(float(mx), float(my), "+", color="lime", ms=11, mew=1.5)
            ax.annotate(lab, (float(mx), float(my)), xytext=(5, 5), textcoords="offset points", color="lime", fontsize=9)
    ax_full.add_patch(plt.Rectangle((zwin[0], zwin[2]), 2 * half, 2 * half, fill=False, color="white", lw=0.8))
    ax_lc.plot(range(len(times)), peaks / 1e5, "o-", color="tab:blue")
    tick = list(range(0, len(times), max(1, len(times) // 12)))
    ax_lc.set_xticks(tick); ax_lc.set_xticklabels([labels[i] for i in tick], fontsize=8)
    ax_lc.set_ylabel("MWA peak [10⁵ Jy/beam]"); ax_lc.set_xlabel(f"UTC, 2022-09-30 ({step:.0f} s steps)")
    marker = ax_lc.axvline(0, color="red", lw=1.5)
    contours = []
    title = fig.suptitle("")

    def draw(i):
        nonlocal contours
        for c in contours:
            c.remove()
        contours = [ax.contour(imgs[i], levels=[f * gmax for f in LEVELS], extent=ext, origin="lower",
                               colors="cyan", linewidths=1.0) for ax in (ax_full, ax_zoom)]
        marker.set_xdata([i, i])
        title.set_text(f"MWA {freqs[k]:.1f} MHz (P-AIRCARS, {step:.0f} s) {labels[i]} UTC on AIA {wav} Å {smap.date.isot[11:19]};"
                       f" contours {', '.join(f'{int(f*100)}' for f in LEVELS)} % of {gmax:.2g} Jy/beam")
        return contours

    fig.tight_layout()
    ip = int(np.argmax(peaks))
    draw(ip)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(f"{a.out}_peak.png", dpi=120)
    anim = FuncAnimation(fig, draw, frames=len(times), blit=False)
    anim.save(f"{a.out}.gif", writer=PillowWriter(fps=a.fps), dpi=90)
    print(f"wrote {a.out}_peak.png, {a.out}.gif")
    if shutil.which("ffmpeg"):
        anim.save(f"{a.out}.mp4", writer=FFMpegWriter(fps=a.fps), dpi=120)
        print(f"wrote {a.out}.mp4")


if __name__ == "__main__":
    main()
