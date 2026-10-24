"""MWA movie of one observation at several channels: one panel per channel, same 2 s step.

    python scripts/burst_movie_grid.py cube.npz --out movies/1449551392_allch_s2 [--fps 3]

cube.npz (written by scripts/calculon/export_board.py for a product with layout "grid"):
  times     (T,) ISO strings, the union of the frame start times of all channels
  freqs     (C,) MHz, chans (C,) coarse channel numbers, sorted by frequency
  data_<c>  (T, n_c, n_c) float, NaN where that channel has no image at that time
  extent_<c> [x0, x1, y0, y1] arcsec of that channel's crop (cell sizes differ per channel)

Each panel keeps one colour scale over the whole movie (that channel's maximum), so the
burst rises and fades within a channel; cyan: optical limb and 50/90 % contours of the
frame's peak. Bottom: peak brightness of every channel over time, each normalised to its own
maximum, with a cursor at the current frame; a drifting burst peaks later at lower frequency.
Writes <out>_peak.png (frame with the highest summed normalised peak) and <out>.mp4.
"""

from __future__ import annotations

import argparse
import shutil

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FFMpegWriter, FuncAnimation

R_SUN = 975.0   # arcsec, December; enough for the limb circle at board resolution


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cube")
    ap.add_argument("--out", required=True)
    ap.add_argument("--fps", type=float, default=3)
    ap.add_argument("--ncols", type=int, default=4)
    a = ap.parse_args()

    d = np.load(a.cube, allow_pickle=False)
    times, freqs, chans = d["times"], d["freqs"], d["chans"]
    C, T = len(chans), len(times)
    data = [d[f"data_{c}"] for c in chans]
    ext = [d[f"extent_{c}"] for c in chans]
    pk = np.array([[np.nanmax(x[i]) if np.isfinite(x[i]).any() else np.nan for i in range(T)] for x in data])
    vmax = np.nanmax(pk, axis=1)
    norm = pk / vmax[:, None]
    ip = int(np.nanargmax(np.nansum(norm, axis=0)))
    secs = np.array([(np.datetime64(t[:23]) - np.datetime64(times[0][:23])) / np.timedelta64(1, "ms") / 1e3
                     for t in times])

    nrow = -(-C // a.ncols)
    fig = plt.figure(figsize=(3.1 * a.ncols, 3.0 * nrow + 2.6))
    gs = fig.add_gridspec(nrow + 1, a.ncols, height_ratios=[3] * nrow + [2.2], hspace=0.28, wspace=0.08)
    ims, axes = [], []
    for k in range(C):
        ax = fig.add_subplot(gs[k // a.ncols, k % a.ncols])
        im = ax.imshow(np.zeros((2, 2)), origin="lower", cmap="inferno", vmin=0, vmax=vmax[k], extent=ext[k])
        ax.add_patch(plt.Circle((0, 0), R_SUN, fill=False, color="cyan", lw=0.6))
        ax.set_xlim(-1400, 1400); ax.set_ylim(-1400, 1400)
        ax.set_xticks([]); ax.set_yticks([])
        ax.set_title(f"ch {chans[k]} · {freqs[k]:.1f} MHz", fontsize=9)
        ims.append(im); axes.append(ax)
    ax_lc = fig.add_subplot(gs[nrow, :])
    cmap = plt.get_cmap("viridis")
    for k in range(C):
        ax_lc.plot(secs, norm[k], "-", lw=1.1, color=cmap(k / max(1, C - 1)), label=f"{freqs[k]:.0f}")
    ax_lc.set_xlim(secs[0] - 1, secs[-1] + 3)
    ax_lc.set_ylabel("peak / channel max")
    ax_lc.set_xlabel(f"seconds after {times[0][11:21]} UTC {times[0][:10]} (image start times, 2 s images)")
    ax_lc.legend(title="MHz", fontsize=7, title_fontsize=7, ncol=C, loc="upper left", frameon=False)
    cursor = ax_lc.axvline(secs[ip], color="red", lw=1.2)
    title = fig.suptitle("")
    contours = []

    def draw(i):
        while contours:
            contours.pop().remove()
        for k in range(C):
            img = data[k][i]
            if np.isfinite(img).any():
                ims[k].set_data(np.nan_to_num(img)); ims[k].set_alpha(1.0)
                ny, nx = img.shape
                x0, x1, y0, y1 = ext[k]
                X, Y = np.linspace(x0, x1, nx), np.linspace(y0, y1, ny)
                contours.append(axes[k].contour(X, Y, np.nan_to_num(img), levels=np.nanmax(img) * np.array([0.5, 0.9]),
                                                colors="cyan", linewidths=0.6))
            else:   # no image of this channel at this time (P-AIRCARS dropped it)
                ims[k].set_alpha(0.15)
        cursor.set_xdata([secs[i], secs[i]])
        title.set_text(f"MWA, P-AIRCARS 2 s images starting {times[i][11:21]} UTC; "
                       f"each panel on its own fixed scale; cyan: optical limb, 50/90 % contours")
        return ims

    draw(ip)
    fig.savefig(f"{a.out}_peak.png", dpi=100)
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        import imageio_ffmpeg
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    plt.rcParams["animation.ffmpeg_path"] = ffmpeg
    FuncAnimation(fig, draw, frames=T, blit=False).save(
        f"{a.out}.mp4", writer=FFMpegWriter(fps=a.fps, codec="libx264", extra_args=["-pix_fmt", "yuv420p"]), dpi=90)
    print(f"wrote {a.out}_peak.png, {a.out}.mp4")


if __name__ == "__main__":
    main()
