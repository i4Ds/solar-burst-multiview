"""MWA burst time series as contours over PFSS field lines from AR 13110 on AIA.

    python scripts/burst_movie_pfss.py data/flare20220930/overnight/1348547272_025s_ch116_c2_burst.npz \
        data/flare20220930/gong/mrzqs220930t0404c2262_089.fits.gz \
        data/flare20220930/aia/aia.lev1.193A_2022_09_30T04_28_40.84Z.image_lev1.fits \
        --centroids figures/flare20220930/centroids_042836_44.json \
        --out figures/flare20220930/burst025s_ch116_pfss --fps 8

Field lines as in pfss_fieldlines.py (open green, closed white), traced once.
Contours are fractions of the maximum over all frames, as in burst_movie.py.
--centroids adds the per-channel burst centroids (fixed dots coloured by
frequency, same selection as pfss_fieldlines.py).
Writes <out>_peak.png, <out>.gif and, if ffmpeg is available, <out>.mp4.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

import astropy.units as u
import matplotlib.pyplot as plt
import numpy as np
from astropy.visualization import AsinhStretch, ImageNormalize
from matplotlib.animation import FFMpegWriter, FuncAnimation, PillowWriter
from matplotlib.patches import Circle
from sunpy.coordinates import get_earth
from sunpy.map import Map

from pfss_fieldlines import project_line, trace_ar_lines
from solarburst.maps import aia_hpc_cutout

LEVELS = (0.1, 0.3, 0.5, 0.7, 0.9)
RSUN = 958.0


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("cube", type=Path)
    p.add_argument("gong", type=Path)
    p.add_argument("aia", type=Path)
    p.add_argument("--out", type=Path, required=True, help="output prefix")
    p.add_argument("--ar", nargs=2, type=float, default=(240.0, 158.0), help="AR position, HPC arcsec")
    p.add_argument("--rss", type=float, default=2.5)
    p.add_argument("--win", nargs=4, type=float, default=(-100, 900, -300, 700))
    p.add_argument("--centroids", type=Path, default=None, help="per-channel centroid JSON")
    p.add_argument("--fps", type=float, default=2.0)
    a = p.parse_args()

    d = np.load(a.cube)
    imgs, freqs, times, ext = d["data"][:, 0], d["freqs"], d["times"], d["extent"]
    gmax = np.nanmax(imgs)
    peaks = np.array([np.nanmax(im) for im in imgs])
    secs = [int(t[8:10]) * 3600 + int(t[10:12]) * 60 + float(t[12:]) for t in times]
    step = round((secs[-1] - secs[0]) / (len(secs) - 1), 3) if len(secs) > 1 else 0.0  # times are rounded to 0.1 s
    n = 16 if 0 < step < 1 else 14  # sub-second frames: show tenths
    labels = [f"{t[8:10]}:{t[10:12]}:{t[12:n]}" for t in times]

    smap = Map(str(a.aia))
    t0, earth = smap.date, get_earth(smap.date)
    gmap, lines = trace_ar_lines(a.gong, earth, t0, a.ar, a.rss)
    aia, aext = aia_hpc_cutout(a.aia, fov_arcsec=1300.0)
    aia = aia / smap.exposure_time.to_value(u.s)
    wav = int(smap.wavelength.value)
    win = a.win
    ny, nx = aia.shape
    cols = ((np.array(win[:2]) - aext[0]) / (aext[1] - aext[0]) * nx).astype(int).clip(0, nx)
    rws = ((np.array(win[2:]) - aext[2]) / (aext[3] - aext[2]) * ny).astype(int).clip(0, ny)
    vmax = np.nanpercentile(aia[rws[0]:rws[1], cols[0]:cols[1]], 99.8)

    fig = plt.figure(figsize=(9.5 if a.centroids else 8.5, 10.5))
    gs = fig.add_gridspec(2, 1, height_ratios=[4, 1.1])
    ax, ax_lc = fig.add_subplot(gs[0]), fig.add_subplot(gs[1])
    ax.imshow(aia, origin="lower", extent=aext, cmap=f"sdoaia{wav}",
              norm=ImageNormalize(vmin=0, vmax=vmax, stretch=AsinhStretch(0.02)))
    ax.add_patch(Circle((0, 0), RSUN, fill=False, color="white", lw=0.6, ls="--"))
    n_open = n_closed = 0
    for fl in lines:
        pl = project_line(fl, earth, t0)
        if pl is None:
            continue
        if fl.is_open:
            n_open += 1
            ax.plot(pl[0], pl[1], color="lime", lw=0.8, alpha=0.9)
        else:
            n_closed += 1
            ax.plot(pl[0], pl[1], color="white", lw=0.5, alpha=0.5)
    if a.centroids:
        rows = [r for r in json.load(open(a.centroids)) if r["snr"] > 50 and r["rho"] < 600]
        sc = ax.scatter([r["x"] for r in rows], [r["y"] for r in rows], c=[r["freq"] for r in rows],
                        cmap="plasma", s=40, edgecolor="k", zorder=5)
        fig.colorbar(sc, ax=ax, fraction=0.046, label="MWA centroid frequency [MHz], 04:28:36–44")
    ax.plot(*a.ar, "+", color="yellow", ms=14, mew=2)
    ax.annotate("AR 13110", a.ar, xytext=(-80, 10), textcoords="offset points", color="yellow")
    ax.set_xlim(win[0], win[1]); ax.set_ylim(win[2], win[3]); ax.set_aspect("equal")
    ax.set_xlabel("Solar X [arcsec]"); ax.set_ylabel("Solar Y [arcsec]")
    ax_lc.plot(range(len(times)), peaks / 1e5, "o-", color="tab:blue", ms=3)
    tick = list(range(0, len(times), max(1, len(times) // 8)))
    ax_lc.set_xticks(tick); ax_lc.set_xticklabels([labels[i] for i in tick], fontsize=8)
    ax_lc.set_ylabel("MWA peak [10⁵ Jy/beam]"); ax_lc.set_xlabel(f"UTC, 2022-09-30 ({step:g} s steps)")
    marker = ax_lc.axvline(0, color="red", lw=1.5)
    title = fig.suptitle("", fontsize=9)
    contours = []

    def draw(i):
        nonlocal contours
        for c in contours:
            c.remove()
        contours = [ax.contour(imgs[i], levels=[f * gmax for f in LEVELS], extent=ext, origin="lower",
                               colors="cyan", linewidths=1.2)]
        marker.set_xdata([i, i])
        title.set_text(f"MWA {freqs[0]:.1f} MHz (P-AIRCARS, {step:g} s) {labels[i]} UTC, contours "
                       f"{', '.join(f'{int(f*100)}' for f in LEVELS)} % of {gmax:.2g} Jy/beam\n"
                       f"PFSS (GONG {gmap.date.isot[:16]}, Rss {a.rss} R☉) from AR 13110: open (green) {n_open}, "
                       f"closed (white) {n_closed}; AIA {wav} Å {t0.isot[11:19]}")
        return contours

    fig.tight_layout(rect=(0, 0, 1, 0.955))  # room for the two-line title
    draw(int(np.argmax(peaks)))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(f"{a.out}_peak.png", dpi=120)
    anim = FuncAnimation(fig, draw, frames=len(times), blit=False)
    anim.save(f"{a.out}.gif", writer=PillowWriter(fps=a.fps), dpi=80)
    print(f"wrote {a.out}_peak.png, {a.out}.gif")
    if shutil.which("ffmpeg"):
        anim.save(f"{a.out}.mp4", writer=FFMpegWriter(fps=a.fps), dpi=120)
        print(f"wrote {a.out}.mp4")


if __name__ == "__main__":
    main()
