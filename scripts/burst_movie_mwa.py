"""MWA-only burst movie with heliographic grid: full Sun and zoom, one colour scale.

    python scripts/burst_movie_mwa.py data/flare20220930/overnight/burst10_ch116.npz \
        --out figures/flare20220930/burst10_ch116_mwa --zoom 300 120 600 --grid 15

The cube comes from scripts/calculon/overnight/make_cube.py (P-AIRCARS HPC
images, Stokes I, square grid centred on Sun centre). Each frame is wrapped in
a sunpy Map (observer Earth) so that Stonyhurst latitude/longitude lines and the
limb are drawn with sunpy. Writes <out>_peak.png, <out>.gif and <out>.mp4
(if ffmpeg is available).
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

import astropy.units as u
import matplotlib.pyplot as plt
import numpy as np
from astropy.coordinates import SkyCoord
from astropy.time import Time
from matplotlib.animation import FFMpegWriter, FuncAnimation, PillowWriter
from sunpy.coordinates import Helioprojective, get_earth
from sunpy.map import Map, make_fitswcs_header


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("cube", type=Path)
    p.add_argument("--out", type=Path, required=True, help="output prefix")
    p.add_argument("--freq", type=float, default=None)
    p.add_argument("--zoom", nargs=3, type=float, default=(300, 120, 600), metavar=("X", "Y", "HALF"))
    p.add_argument("--fov", type=float, default=1500.0)
    p.add_argument("--grid", type=float, default=15.0, help="grid spacing, deg")
    p.add_argument("--fps", type=float, default=2.0)
    a = p.parse_args()

    d = np.load(a.cube)
    cube, freqs, times, ext = d["data"], d["freqs"], d["times"], d["extent"]
    k = 0 if a.freq is None else int(np.argmin(np.abs(freqs - a.freq)))
    imgs = np.nan_to_num(cube[:, k], nan=0.0)
    gmax = float(np.max(imgs))
    peaks = imgs.reshape(len(imgs), -1).max(axis=1)
    labels = [f"{t[8:10]}:{t[10:12]}:{t[12:14]}" for t in times]
    n = imgs.shape[-1]
    cell = (ext[1] - ext[0]) / n
    ip = int(np.argmax(peaks))
    t0 = Time(f"{times[ip][:4]}-{times[ip][4:6]}-{times[ip][6:8]}T{times[ip][8:10]}:{times[ip][10:12]}:{times[ip][12:]}")
    centre = SkyCoord(0 * u.arcsec, 0 * u.arcsec, frame=Helioprojective(observer=get_earth(t0), obstime=t0))
    header = make_fitswcs_header(imgs[ip], centre, scale=[cell, cell] * u.arcsec / u.pix,
                                 telescope="MWA", instrument="P-AIRCARS", wavelength=freqs[k] * u.MHz)
    smap = Map(imgs[ip], header)

    def pix(xy_arcsec):  # arcsec -> pixel index along an axis (grid centred on 0)
        return np.asarray(xy_arcsec) / cell + (n - 1) / 2.0

    fig = plt.figure(figsize=(12, 7.8))
    gs = fig.add_gridspec(2, 2, height_ratios=[4, 1.1])
    ax_full = fig.add_subplot(gs[0, 0], projection=smap)
    ax_zoom = fig.add_subplot(gs[0, 1], projection=smap)
    ax_lc = fig.add_subplot(gs[1, :])
    ims = []
    x, y, half = a.zoom
    for ax, (x0, x1, y0, y1) in ((ax_full, (-a.fov, a.fov, -a.fov, a.fov)),
                                 (ax_zoom, (x - half, x + half, y - half, y + half))):
        im = ax.imshow(imgs[ip], origin="lower", cmap="inferno", vmin=0, vmax=gmax)
        ims.append(im)
        grid = smap.draw_grid(axes=ax, grid_spacing=a.grid * u.deg, color="white", lw=0.5, alpha=0.6)
        for c in grid:  # grid spacing is in the title; tick labels would collide with the colour bar
            c.set_ticklabel_visible(False)
            c.set_ticks_visible(False)
            c.set_axislabel("")
        smap.draw_limb(axes=ax, color="cyan", lw=0.8)
        ax.set_xlim(pix(x0), pix(x1)); ax.set_ylim(pix(y0), pix(y1))
        ax.coords[0].set_axislabel("Solar X [arcsec]"); ax.coords[1].set_axislabel("Solar Y [arcsec]")
        ax.coords[0].set_format_unit(u.arcsec); ax.coords[1].set_format_unit(u.arcsec)
    zx0, zy0 = pix(x - half), pix(y - half)
    ax_full.add_patch(plt.Rectangle((zx0, zy0), 2 * half / cell, 2 * half / cell, fill=False, color="white", lw=0.8))
    cb = fig.colorbar(ims[1], ax=[ax_full, ax_zoom], fraction=0.025, pad=0.04)
    cb.set_label("Jy/beam (Stokes I, primary-beam corrected)")
    ax_lc.plot(range(len(times)), peaks / 1e5, "o-")
    ax_lc.set_xticks(range(len(times))); ax_lc.set_xticklabels(labels, fontsize=8)
    ax_lc.set_ylabel("peak [10⁵ Jy/beam]"); ax_lc.set_xlabel("UTC, 2022-09-30 (4 s steps)")
    marker = ax_lc.axvline(ip, color="red", lw=1.5)
    title = fig.suptitle("")

    def draw(i):
        for im in ims:
            im.set_data(imgs[i])
        marker.set_xdata([i, i])
        title.set_text(f"MWA {freqs[k]:.1f} MHz, P-AIRCARS 4 s, {labels[i]} UTC; Stonyhurst grid {a.grid:g}°, cyan: optical limb")
        return ims

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
