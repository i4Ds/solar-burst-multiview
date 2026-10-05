"""MWA image of the 2022-09-30 flare in helioprojective coordinates, over AIA.

    python scripts/flare_overlay.py figures/flare20220930/1348545200_ch113_peak-image.fits \
        data/flare20220930/aia/aia.lev1.193A_*.fits data/flare20220930/aia/aia.lev1.131A_*.fits \
        --contour-map stix_clean_..._earth.fits:"STIX 4-10 keV" --zoom -867 397 200
"""

from __future__ import annotations

import argparse
from pathlib import Path

import astropy.units as u
import matplotlib.pyplot as plt
import numpy as np
import sunpy.visualization.colormaps  # noqa: F401  registers sdoaia* colormaps
from astropy.time import Time
from astropy.visualization import AsinhStretch, ImageNormalize
from matplotlib.lines import Line2D
from matplotlib.patches import Circle, Ellipse
from sunpy.coordinates import sun
from sunpy.map import Map

from solarburst.maps import aia_hpc_cutout, load_casa_2d, radec_to_hpc

LEVELS = (0.1, 0.3, 0.5, 0.7, 0.9)
OVERLAY_LEVELS = (0.3, 0.5, 0.7, 0.9)
CONTOUR_COLOURS = ("magenta", "yellow", "white")


def _aia(path: Path, fov: float) -> tuple[np.ndarray, list[float], int, str]:
    smap = Map(str(path))
    img, ext = aia_hpc_cutout(path, fov_arcsec=fov)
    wav = int(smap.wavelength.value)
    return img / smap.exposure_time.to_value(u.s), ext, wav, smap.date.isot[11:19]


def _show_aia(ax, img, ext, wav, window=None) -> None:
    """Asinh stretch; ``window`` (x0, x1, y0, y1) sets vmax from that region only."""
    sub = img
    if window is not None:
        ny, nx = img.shape
        cols = ((np.array(window[:2]) - ext[0]) / (ext[1] - ext[0]) * nx).astype(int).clip(0, nx)
        rows = ((np.array(window[2:]) - ext[2]) / (ext[3] - ext[2]) * ny).astype(int).clip(0, ny)
        sub = img[rows[0]:rows[1], cols[0]:cols[1]]
    norm = ImageNormalize(vmin=0, vmax=np.nanpercentile(sub, 99.9), stretch=AsinhStretch(0.02))
    ax.imshow(img, origin="lower", extent=ext, cmap=f"sdoaia{wav}", norm=norm)


def _map_extent(m) -> list[float]:
    bl, tr = m.bottom_left_coord, m.top_right_coord
    return [bl.Tx.to_value(u.arcsec), tr.Tx.to_value(u.arcsec), bl.Ty.to_value(u.arcsec), tr.Ty.to_value(u.arcsec)]


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("radio", type=Path)
    p.add_argument("aia", type=Path, nargs="*")
    p.add_argument("--fov", type=float, default=1300.0, help="half width, arcsec")
    p.add_argument("--mark", action="append", default=[], metavar="LABEL:X:Y",
                   help="HPC position (arcsec) to mark, e.g. 'M1.1:-867:397'")
    p.add_argument("--contour-map", action="append", default=[], metavar="FITS:LABEL",
                   help="Earth-view HPC map (unrotated) to contour at 30-90 %% of its peak")
    p.add_argument("--zoom", nargs=3, type=float, metavar=("X", "Y", "HALF"),
                   help="extra panel on the last AIA image around (X, Y), arcsec")
    p.add_argument("--out", type=Path)
    args = p.parse_args()

    data, header = load_casa_2d(args.radio)
    t = Time(header["DATE-OBS"])
    hpc, ext = radec_to_hpc(data, header, fov_arcsec=args.fov)
    peak = np.nanmax(hpc)
    iy, ix = np.unravel_index(np.nanargmax(hpc), hpc.shape)
    cell = (ext[1] - ext[0]) / hpc.shape[1]
    px, py = ext[0] + (ix + 0.5) * cell, ext[2] + (iy + 0.5) * cell
    rsun = sun.angular_radius(t).to_value(u.arcsec)
    mhz = header["CRVAL3"] / 1e6
    print(f"P = {sun.P(t).deg:.2f} deg, radio peak {peak:.4g} Jy/beam at ({px:.0f}\", {py:.0f}\")")

    overlays = []
    for item, colour in zip(args.contour_map, CONTOUR_COLOURS):
        path, _, label = item.partition(":")
        m = Map(path)
        overlays.append((np.asarray(m.data, dtype=float), _map_extent(m), label or Path(path).stem, colour))

    aia = [_aia(path, args.fov) for path in args.aia]
    npanel = 1 + len(aia) + bool(args.zoom and aia)
    fig, axs = plt.subplots(1, npanel, figsize=(5.6 * npanel, 5.6), squeeze=False)
    axs = axs[0]
    im = axs[0].imshow(hpc, origin="lower", extent=ext, cmap="inferno", vmin=0, vmax=peak)
    fig.colorbar(im, ax=axs[0], fraction=0.046, label="Jy/beam (not flux-calibrated)")
    axs[0].set_title(f"MWA {mhz:.1f} MHz  {t.isot[:19]} +4 s")

    limits = [(-args.fov, args.fov, -args.fov, args.fov)] * npanel
    for ax, (img, aext, wav, when) in zip(axs[1:], aia):
        _show_aia(ax, img, aext, wav)
        ax.set_title(f"AIA {wav} Å {when}")
    if npanel > 1 + len(aia):
        x, y, half = args.zoom
        window = (x - half, x + half, y - half, y + half)
        img, aext, wav, when = aia[-1]
        _show_aia(axs[-1], img, aext, wav, window)
        axs[-1].set_title(f"AIA {wav} Å {when}, zoom")
        limits[-1] = window

    bmaj, bmin = header["BMAJ"] * 3600, header["BMIN"] * 3600
    for ax, (x0, x1, y0, y1) in zip(axs, limits):
        if ax is not axs[0]:
            ax.contour(hpc, levels=[f * peak for f in LEVELS], extent=ext, origin="lower",
                       colors="cyan", linewidths=0.9)
        for odata, oext, _, colour in overlays:
            ax.contour(odata, levels=[f * np.nanmax(odata) for f in OVERLAY_LEVELS], extent=oext,
                       origin="lower", colors=colour, linewidths=1.0)
        ax.add_patch(Circle((0, 0), rsun, fill=False, color="white", lw=0.7, ls="--"))
        ax.set_xlim(x0, x1)
        ax.set_ylim(y0, y1)
        ax.set_aspect("equal")
        ax.set_xlabel("Solar X [arcsec]")
        ax.set_ylabel("Solar Y [arcsec]")
        for mark in args.mark:
            label, mx, my = mark.rsplit(":", 2)
            if x0 <= float(mx) <= x1 and y0 <= float(my) <= y1:
                ax.plot(float(mx), float(my), "+", color="lime", ms=12, mew=1.5)
                ax.annotate(label, (float(mx), float(my)), xytext=(6, 6), textcoords="offset points",
                            color="lime", fontsize=9)
    handles = [Line2D([], [], color="cyan", label=f"MWA {mhz:.1f} MHz, {', '.join(f'{int(f*100)}' for f in LEVELS)} %")]
    handles += [Line2D([], [], color=colour, label=f"{label}, {', '.join(f'{int(f*100)}' for f in OVERLAY_LEVELS)} %")
                for _, _, label, colour in overlays]
    axs[-1].legend(handles=handles, loc="lower right", fontsize=8, framealpha=0.7)
    # wsclean BPA is east of north in the sky; rotate into solar coordinates.
    axs[0].add_patch(Ellipse((-args.fov + 1.2 * bmaj, -args.fov + 1.2 * bmaj), bmin, bmaj,
                             angle=header["BPA"] - sun.P(t).deg, color="white"))
    fig.suptitle("2022-09-30 M1.1 flare (STIX 2209300352), contours in % of each peak")
    fig.tight_layout()
    out = args.out or args.radio.with_name(args.radio.name.replace("-image.fits", "_hpc_aia.png"))
    fig.savefig(out, dpi=130)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
