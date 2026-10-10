"""Compare a hyperdrive/wsclean image with P-AIRCARS images of the same 4 s step, on AIA.

    python scripts/compare_paircars.py figures/flare20220930/1348547272_ch112_042844_noaof-image.fits \
        data/flare20220930/aia/aia.lev1.193A_2022_09_30T04_28_40.84Z.image_lev1.fits \
        --paircars "3C444 only:data/.../basiccal_only/images/pbcor_hpcs/time_20220930042844.0_..._HPC.fits" \
        --paircars "self-cal:data/.../selfcal/images/pbcor_hpcs/time_20220930042844.0_..._HPC.fits" \
        --zoom 240 158 450 --mark AR13110:240:158

P-AIRCARS ``*_HPC.fits`` are helioprojective maps (Stokes I is the first plane).
Each panel shows one image with its 30-90 % contours and the AIA image below;
the last panel overlays every image's 50 % contour and marks each peak.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import astropy.units as u
import matplotlib.pyplot as plt
import numpy as np
from astropy.io import fits
from astropy.visualization import AsinhStretch, ImageNormalize
from matplotlib.lines import Line2D
from matplotlib.patches import Circle
from sunpy.coordinates import sun
from sunpy.map import Map

from solarburst.maps import aia_hpc_cutout, load_casa_2d, radec_to_hpc

LEVELS = (0.3, 0.5, 0.7, 0.9)
COLOURS = ("cyan", "magenta", "yellow", "lime")


def paircars_hpc(path: Path) -> tuple[np.ndarray, list[float], dict]:
    """Stokes I plane and imshow extent (arcsec) of a P-AIRCARS HPC FITS."""
    with fits.open(path) as hdul:
        data = np.squeeze(hdul[0].data).astype(float)
        hd = hdul[0].header
    if data.ndim == 3:
        data = data[0]
    ny, nx = data.shape
    cd1, cd2 = float(hd["CDELT1"]), float(hd["CDELT2"])
    x0 = hd["CRVAL1"] + (1 - hd["CRPIX1"] - 0.5) * cd1
    y0 = hd["CRVAL2"] + (1 - hd["CRPIX2"] - 0.5) * cd2
    beam = {"bmaj": hd["BMAJ"] * 3600, "bmin": hd["BMIN"] * 3600}
    return data, [x0, x0 + nx * cd1, y0, y0 + ny * cd2], beam


def peak_xy(data: np.ndarray, ext: list[float]) -> tuple[float, float]:
    iy, ix = np.unravel_index(np.nanargmax(data), data.shape)
    cx = (ext[1] - ext[0]) / data.shape[1]
    cy = (ext[3] - ext[2]) / data.shape[0]
    return ext[0] + (ix + 0.5) * cx, ext[2] + (iy + 0.5) * cy


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("radio", type=Path, help="wsclean image (RA/Dec)")
    p.add_argument("aia", type=Path)
    p.add_argument("--label", default="hyperdrive + wsclean")
    p.add_argument("--paircars", action="append", default=[], metavar="LABEL:FITS")
    p.add_argument("--zoom", nargs=3, type=float, default=(240, 158, 450), metavar=("X", "Y", "HALF"))
    p.add_argument("--mark", action="append", default=[], metavar="LABEL:X:Y")
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()

    data, header = load_casa_2d(args.radio)
    hpc, ext = radec_to_hpc(data, header, fov_arcsec=1300.0)
    maps = [(args.label, hpc, ext, header["BMAJ"] * 3600, header["BMIN"] * 3600)]
    for item in args.paircars:
        label, path = item.split(":", 1)
        d, e, b = paircars_hpc(Path(path))
        maps.append((label, d, e, b["bmaj"], b["bmin"]))

    smap = Map(str(args.aia))
    aia, aext = aia_hpc_cutout(args.aia, fov_arcsec=1300.0)
    aia = aia / smap.exposure_time.to_value(u.s)
    x, y, half = args.zoom
    win = (x - half, x + half, y - half, y + half)
    t = smap.date
    rsun = sun.angular_radius(t).to_value(u.arcsec)

    n = len(maps) + 1
    fig, axs = plt.subplots(1, n, figsize=(5.2 * n, 5.4), squeeze=False)
    axs = axs[0]
    for ax in axs:
        ny, nx = aia.shape
        cols = ((np.array(win[:2]) - aext[0]) / (aext[1] - aext[0]) * nx).astype(int).clip(0, nx)
        rows = ((np.array(win[2:]) - aext[2]) / (aext[3] - aext[2]) * ny).astype(int).clip(0, ny)
        vmax = np.nanpercentile(aia[rows[0]:rows[1], cols[0]:cols[1]], 99.9)
        ax.imshow(aia, origin="lower", extent=aext, cmap=f"sdoaia{int(smap.wavelength.value)}",
                  norm=ImageNormalize(vmin=0, vmax=vmax, stretch=AsinhStretch(0.02)))
        ax.add_patch(Circle((0, 0), rsun, fill=False, color="white", lw=0.7, ls="--"))
        ax.set_xlim(win[0], win[1])
        ax.set_ylim(win[2], win[3])
        ax.set_aspect("equal")
        ax.set_xlabel("Solar X [arcsec]")
        for mark in args.mark:
            label, mx, my = mark.rsplit(":", 2)
            ax.plot(float(mx), float(my), "+", color="white", ms=12, mew=1.5)
            ax.annotate(label, (float(mx), float(my)), xytext=(6, 6), textcoords="offset points",
                        color="white", fontsize=9)
    axs[0].set_ylabel("Solar Y [arcsec]")

    handles = []
    for ax, (label, d, e, bmaj, bmin), colour in zip(axs, maps, COLOURS):
        peak = np.nanmax(d)
        ax.contour(d, levels=[f * peak for f in LEVELS], extent=e, origin="lower", colors=colour, linewidths=1.0)
        px, py = peak_xy(d, e)
        ax.plot(px, py, "x", color=colour, ms=10, mew=2)
        ax.set_title(f"{label}\npeak ({px:+.0f}″, {py:+.0f}″), beam {bmaj / 60:.1f}′×{bmin / 60:.1f}′", fontsize=9)
        axs[-1].contour(d, levels=[0.5 * peak], extent=e, origin="lower", colors=colour, linewidths=1.3)
        axs[-1].plot(px, py, "x", color=colour, ms=10, mew=2)
        handles.append(Line2D([], [], color=colour, label=f"{label} (50 %, × peak)"))
        print(f"{label:28s} peak ({px:+7.1f}, {py:+7.1f}) arcsec  max {peak:.4g}")
    axs[-1].set_title("all, 50 % contour", fontsize=9)
    axs[-1].legend(handles=handles, loc="lower right", fontsize=8, framealpha=0.8)
    fig.suptitle(f"MWA 143.4 MHz {header['DATE-OBS'][:19]} (4 s) on AIA {int(smap.wavelength.value)} Å {t.isot[11:19]}; contours {', '.join(f'{int(f*100)}' for f in LEVELS)} % of each peak")
    fig.tight_layout()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.out, dpi=120)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
