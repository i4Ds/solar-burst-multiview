#!/usr/bin/env python3
"""One 0.5 s SuperUniform snapshot: Rohit's CORRECTED_DATA vs our CASA applycal.

Same time, same CASA numbers, 108 MHz pair. Rohit's Cen A ``.cal.p`` table,
not P-AIRCARS. Not Figure 4.
"""

from __future__ import annotations

import os
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from astropy.io import fits
from casatasks import exportfits, rmtables, tclean
from casatools import msmetadata
from matplotlib.patches import Circle

PHASECENTER = "J2000 16h40m55.28s -19d40m25.38s"
TRANGE = "2015/12/03/03:42:04.0~2015/12/03/03:42:04.5"
ROHIT = "/mnt/nas05/data02/rohit/20151203_MWA/new_ms/108MHz/1133149192-084-085.ms"
OURS = (
    f"/scratch/{os.environ['USER']}/mwa/sharma2020/raw/"
    "cal_0p5s_casa/1133149192_ch84-85_0p5s.ms"
)
OUT = Path(f"/scratch/{os.environ['USER']}/mwa/sharma2020/raw/cal_0p5s_casa/inspect")
RSUN = 958.0
CELL = 50.0


def chanfreqs(ms: str) -> np.ndarray:
    md = msmetadata()
    md.open(ms)
    freqs = np.asarray(md.chanfreqs(0))
    md.close()
    md.done()
    return freqs


def matching_spw(rohit: str, ours: str) -> str:
    rf = chanfreqs(rohit)
    of = chanfreqs(ours)
    lo, hi = float(of.min()), float(of.max())
    idx = [i for i, f in enumerate(rf) if lo - 1e3 <= f <= hi + 1e3]
    if not idx:
        raise RuntimeError(f"no Rohit channels in {lo}-{hi} Hz")
    spw = f"0:{min(idx)}~{max(idx)}"
    print(
        f"ours {of.size} chans {of.min()/1e6:.4f}-{of.max()/1e6:.4f} MHz",
        flush=True,
    )
    print(
        f"rohit spw={spw} {rf[min(idx)]/1e6:.4f}-{rf[max(idx)]/1e6:.4f} MHz "
        f"({len(idx)} of {rf.size})",
        flush=True,
    )
    return spw


def image(ms: str, prefix: Path, spw: str) -> Path:
    for suf in (".image", ".model", ".psf", ".residual", ".pb", ".sumwt", ".mask"):
        rmtables(str(prefix) + suf)
    tclean(
        vis=ms,
        imagename=str(prefix),
        datacolumn="corrected",
        spw=spw,
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
    print(f"wrote {fits_path}", flush=True)
    return fits_path


def load_crop(fits_path: Path) -> tuple[np.ndarray, float]:
    with fits.open(fits_path) as hdul:
        data = np.squeeze(hdul[0].data).astype(np.float64)
    ny, nx = data.shape
    half = 50
    cy, cx = ny // 2, nx // 2
    crop = data[cy - half : cy + half, cx - half : cx + half]
    peak = float(np.nanmax(crop))
    return crop, peak


def draw(ax, crop: np.ndarray, peak: float, vmax: float, title: str) -> None:
    half = crop.shape[0] // 2
    shown = np.where(crop > 0.12 * peak, crop, np.nan) if peak > 0 else crop
    ax.imshow(
        shown,
        origin="lower",
        extent=[-half * CELL, half * CELL, -half * CELL, half * CELL],
        cmap="jet",
        vmin=0,
        vmax=max(vmax, 1e-6),
        interpolation="nearest",
    )
    ax.add_patch(Circle((0, 0), RSUN, fill=False, color="saddlebrown", lw=0.8))
    ax.add_patch(
        Circle((0, 0), 2 * RSUN, fill=False, color="saddlebrown", lw=0.8, ls="--")
    )
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


def save_pair(
    rohit: np.ndarray,
    rp: float,
    ours: np.ndarray,
    op: float,
    vmax: float,
    path: Path,
    subtitle: str,
) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 4.6), constrained_layout=True)
    draw(axes[0], rohit, rp, vmax, "Rohit  0.5 s at 03:42:04")
    draw(axes[1], ours, op, vmax, "CASA applycal of his Cen A table")
    fig.suptitle(
        f"108 MHz SuperUniform. {subtitle}. Not Figure 4.",
        fontsize=11,
    )
    fig.savefig(path, dpi=140, facecolor="white")
    plt.close(fig)
    print(f"wrote {path}", flush=True)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    os.chdir(OUT)
    spw = matching_spw(ROHIT, OURS)
    rohit_fits = image(ROHIT, OUT / "rohit_ch84_034204", spw)
    ours_fits = image(OURS, OUT / "ours_ch84_034204", "")
    rohit, rp = load_crop(rohit_fits)
    ours, op = load_crop(ours_fits)
    save_pair(
        rohit,
        rp,
        ours,
        op,
        max(rp, op),
        OUT / "fig4_snap_rohit_vs_casa.png",
        "shared colour scale",
    )
    save_pair(
        rohit,
        rp,
        ours,
        op,
        rp,
        OUT / "fig4_snap_rohit_vs_casa_rohit_scale.png",
        "colour scale set to Rohit's peak",
    )
    save_pair(
        rohit,
        rp,
        ours,
        op,
        op if op > 0 else rp,
        OUT / "fig4_snap_rohit_vs_casa_shape.png",
        "each panel on its own peak",
    )
    print("COMPARE_SNAP_OK", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
