"""MWA image of the 2022-09-30 flare in helioprojective coordinates, over AIA.

    python scripts/flare_overlay.py figures/flare20220930/1348545200_ch113_peak-image.fits \
        data/flare20220930/aia/aia.lev1.193A_*.fits data/flare20220930/aia/aia.lev1.131A_*.fits
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
from matplotlib.patches import Circle, Ellipse
from sunpy.coordinates import sun
from sunpy.map import Map

from solarburst.maps import aia_hpc_cutout, load_casa_2d, radec_to_hpc

LEVELS = (0.1, 0.3, 0.5, 0.7, 0.9)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("radio", type=Path)
    p.add_argument("aia", type=Path, nargs="*")
    p.add_argument("--fov", type=float, default=1300.0, help="half width, arcsec")
    p.add_argument("--mark", action="append", default=[], metavar="LABEL:X:Y",
                   help="HPC position (arcsec) to mark, e.g. 'M1.1:-867:397'")
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

    fig, axs = plt.subplots(1, 1 + len(args.aia), figsize=(5.6 * (1 + len(args.aia)), 5.6), squeeze=False)
    axs = axs[0]
    im = axs[0].imshow(hpc, origin="lower", extent=ext, cmap="inferno", vmin=0, vmax=peak)
    fig.colorbar(im, ax=axs[0], fraction=0.046, label="Jy/beam (not flux-calibrated)")
    axs[0].set_title(f"MWA {mhz:.1f} MHz  {t.isot[:19]} +4 s")

    for ax, path in zip(axs[1:], args.aia):
        smap = Map(str(path))
        img, aext = aia_hpc_cutout(path, fov_arcsec=args.fov)
        img = img / smap.exposure_time.to_value(u.s)
        norm = ImageNormalize(vmin=0, vmax=np.nanpercentile(img, 99.9), stretch=AsinhStretch(0.02))
        ax.imshow(img, origin="lower", extent=aext, cmap=f"sdoaia{int(smap.wavelength.value)}", norm=norm)
        ax.contour(hpc, levels=[f * peak for f in LEVELS], extent=ext, origin="lower",
                   colors="cyan", linewidths=0.9)
        ax.set_title(f"AIA {int(smap.wavelength.value)} Å {smap.date.isot[11:19]} + MWA contours")

    bmaj, bmin = header["BMAJ"] * 3600, header["BMIN"] * 3600
    for ax in axs:
        ax.add_patch(Circle((0, 0), rsun, fill=False, color="white", lw=0.7, ls="--"))
        ax.set_xlim(-args.fov, args.fov)
        ax.set_ylim(-args.fov, args.fov)
        ax.set_aspect("equal")
        ax.set_xlabel("Solar X [arcsec]")
        ax.set_ylabel("Solar Y [arcsec]")
        for mark in args.mark:
            label, x, y = mark.rsplit(":", 2)
            ax.plot(float(x), float(y), "+", color="lime", ms=12, mew=1.5)
            ax.annotate(label, (float(x), float(y)), xytext=(6, 6), textcoords="offset points",
                        color="lime", fontsize=9)
    # wsclean BPA is east of north in the sky; rotate into solar coordinates.
    axs[0].add_patch(Ellipse((-args.fov + 1.2 * bmaj, -args.fov + 1.2 * bmaj), bmin, bmaj,
                             angle=header["BPA"] - sun.P(t).deg, color="white"))
    fig.suptitle(f"2022-09-30 M1.1 flare (STIX 2209300352), contours {', '.join(f'{int(f*100)}' for f in LEVELS)} % of peak")
    fig.tight_layout()
    out = args.out or args.radio.with_name(args.radio.name.replace("-image.fits", "_hpc_aia.png"))
    fig.savefig(out, dpi=130)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
