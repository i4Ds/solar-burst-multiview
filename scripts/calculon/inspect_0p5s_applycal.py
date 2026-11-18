#!/usr/bin/env python3
"""One 0.5 s applycal set: cadence, visibilities, and one snapshot of DATA vs CORRECTED_DATA."""

from __future__ import annotations

import os
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from astropy.io import fits
from casatasks import exportfits, tclean
from casatools import table as casa_table
from matplotlib.patches import Circle

MS = Path(
    f"/scratch/{os.environ['USER']}/mwa/sharma2020/raw/cal_0p5s/1133149192_ch84_0p5s.ms"
)
OUT = Path(f"/scratch/{os.environ['USER']}/mwa/sharma2020/raw/cal_0p5s/inspect")
PHASECENTER = "J2000 16h40m55.28s -19d40m25.38s"
TRANGE = "2015/12/03/03:42:04.0~2015/12/03/03:42:04.5"
RSUN = 958.0


def cadence(ms: str) -> None:
    tb = casa_table()
    tb.open(ms)
    interval = np.unique(np.round(tb.getcol("INTERVAL"), 4))
    n = tb.nrows()
    tb.close()
    print(f"nrows={n} INTERVAL={interval.tolist()}", flush=True)


def vis_plot(ms: str, path: Path) -> None:
    tb = casa_table()
    tb.open(ms)
    n = tb.nrows()
    # Mid-scan block so we are not sitting in the flagged start of the file.
    start = max(0, n // 2 - 4000)
    uvw = tb.getcol("UVW", start, 8000)
    data = tb.getcol("DATA", start, 8000)
    corr = tb.getcol("CORRECTED_DATA", start, 8000)
    flag = tb.getcol("FLAG", start, 8000)
    tb.close()
    uv = np.hypot(uvw[0], uvw[1])
    stokes_i = 0.5 * (data[0] + data[3])
    stokes_c = 0.5 * (corr[0] + corr[3])
    d = np.nanmean(np.abs(stokes_i), axis=0)
    c = np.nanmean(np.abs(stokes_c), axis=0)
    ok = ~np.all(flag, axis=(0, 1))
    if int(ok.sum()) < 50:
        ok = np.ones(d.size, dtype=bool)
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    ax.scatter(uv[ok], d[ok], s=4, alpha=0.25, label="DATA", color="#4c78a8")
    ax.scatter(uv[ok], c[ok], s=4, alpha=0.25, label="CORRECTED_DATA", color="#f58518")
    ax.set_xlabel("Baseline length (m)")
    ax.set_ylabel("Stokes I amplitude")
    ax.set_title("ch 84, 0.5 s set, 8000 rows near mid-scan")
    ax.legend(markerscale=3)
    fig.tight_layout()
    fig.savefig(path, dpi=130, facecolor="white")
    plt.close(fig)
    print(f"wrote {path}  unflagged={int(ok.sum())}", flush=True)


def image_one(ms: str, prefix: Path, column: str) -> Path:
    tclean(
        vis=ms,
        imagename=str(prefix),
        datacolumn=column,
        imsize=[1024, 1024],
        cell="50arcsec",
        phasecenter=PHASECENTER,
        stokes="I",
        specmode="mfs",
        weighting="superuniform",
        npixels=0,
        deconvolver="hogbom",
        niter=8000,
        gain=0.1,
        threshold=0.0,
        pblimit=-1.0,
        savemodel="none",
        restoration=True,
        parallel=False,
        timerange=TRANGE,
        nterms=1,
        interactive=False,
    )
    fits_path = Path(str(prefix) + ".fits")
    exportfits(imagename=str(prefix) + ".image", fitsimage=str(fits_path), overwrite=True)
    return fits_path


def map_plot(fits_path: Path, title: str, ax) -> None:
    with fits.open(fits_path) as hdul:
        data = np.squeeze(hdul[0].data).astype(np.float64)
    ny, nx = data.shape
    cell = 50.0
    extent = [-(nx / 2) * cell, (nx / 2) * cell, -(ny / 2) * cell, (ny / 2) * cell]
    # crude centre crop
    half = 50
    cy, cx = ny // 2, nx // 2
    crop = data[cy - half : cy + half, cx - half : cx + half]
    peak = float(np.nanmax(crop))
    shown = np.where(crop > 0.12 * peak, crop, np.nan) if peak > 0 else crop
    ax.imshow(
        shown,
        origin="lower",
        extent=[-half * cell, half * cell, -half * cell, half * cell],
        cmap="jet",
        vmin=0,
        vmax=max(peak, 1e-6),
        interpolation="nearest",
    )
    ax.add_patch(Circle((0, 0), RSUN, fill=False, color="saddlebrown", lw=0.8))
    ax.add_patch(Circle((0, 0), 2 * RSUN, fill=False, color="saddlebrown", lw=0.8, ls="--"))
    ax.set_xlim(-2500, 2500)
    ax.set_ylim(-2500, 2500)
    ax.set_aspect("equal")
    ax.set_title(title, fontsize=11)
    ax.text(
        0.03,
        0.97,
        f"{peak:.3g} Jy/beam",
        transform=ax.transAxes,
        va="top",
        fontsize=8,
        color="white",
        bbox=dict(boxstyle="round,pad=0.15", fc="black", alpha=0.45, lw=0),
    )


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    os.chdir(OUT)
    print(f"ms={MS}", flush=True)
    cadence(str(MS))
    vis_plot(str(MS), OUT / "uv_amp.png")
    data_fits = image_one(str(MS), OUT / "snap_data", "data")
    corr_fits = image_one(str(MS), OUT / "snap_corrected", "corrected")
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 4.6), constrained_layout=True)
    map_plot(data_fits, "DATA  0.5 s at 03:42:04", axes[0])
    map_plot(corr_fits, "CORRECTED_DATA  0.5 s at 03:42:04", axes[1])
    fig.suptitle("CASA SuperUniform of the applycal test set (ch 84). Not Figure 4.", fontsize=11)
    maps = OUT / "snap_data_vs_corrected.png"
    fig.savefig(maps, dpi=140, facecolor="white")
    plt.close(fig)
    print(f"wrote {maps}", flush=True)
    print("INSPECT_OK", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
