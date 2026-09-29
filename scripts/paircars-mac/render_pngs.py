#!/usr/bin/env python3
"""Write a Stokes I contact sheet and per-image PNGs for a P-AIRCARS image directory.

    python scripts/paircars-mac/render_pngs.py /path/to/imagedir/.../images

Needs astropy, matplotlib, and numpy (the solar-burst-multiview conda env has them).
PNGs are written next to the images directory, in a png/ folder.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from astropy.io import fits

PAT = re.compile(r"time_(\d+\.\d+)_freq_([0-9.]+)_pol_IQUV")
HALF_ARCMIN = 40.0


def extent_of(image: np.ndarray, header) -> list[float]:
    ny, nx = image.shape
    dx = abs(float(header["CDELT1"])) * 60.0
    dy = abs(float(header["CDELT2"])) * 60.0
    return [-(nx / 2) * dx, (nx / 2) * dx, -(ny / 2) * dy, (ny / 2) * dy]


def panel(ax, image, header, vmin, vmax, cmap):
    artist = ax.imshow(
        image,
        origin="lower",
        cmap=cmap,
        vmin=vmin,
        vmax=vmax,
        extent=extent_of(image, header),
        interpolation="nearest",
    )
    ax.set_xlim(-HALF_ARCMIN, HALF_ARCMIN)
    ax.set_ylim(-HALF_ARCMIN, HALF_ARCMIN)
    ax.set_aspect("equal")
    return artist


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("images", type=Path, help="Directory of P-AIRCARS *-IQUV.fits cubes")
    args = parser.parse_args()
    src = args.images
    out = src.parent / "png"
    out.mkdir(exist_ok=True)

    items = []
    for path in sorted(src.glob("*.fits")):
        match = PAT.search(path.name)
        if match is None:
            continue
        data = np.squeeze(fits.getdata(path))
        header = fits.getheader(path)
        items.append(
            {
                "time": match.group(1),
                "freq": float(match.group(2)),
                "data": data,
                "header": header,
                "I": data[0],
            }
        )
    if not items:
        raise SystemExit(f"no IQUV FITS cubes in {src}")

    times = sorted({item["time"] for item in items})
    freqs = sorted({item["freq"] for item in items})
    vmax = float(np.percentile(np.concatenate([item["I"].ravel() for item in items]), 99.5))

    for item in items:
        clock = f"{item['time'][8:10]}:{item['time'][10:12]}:{item['time'][12:14]}"
        fig, ax = plt.subplots(figsize=(5.2, 4.6))
        artist = panel(ax, np.clip(item["I"], 0, None), item["header"], 0, vmax, "inferno")
        ax.set_xlabel("East-West offset (arcmin)")
        ax.set_ylabel("North-South offset (arcmin)")
        ax.set_title(f"Stokes I   {clock} UTC   {item['freq']:.2f} MHz")
        fig.colorbar(artist, ax=ax, fraction=0.046, pad=0.04).set_label("Jy/beam")
        fig.tight_layout()
        fig.savefig(out / f"I_{item['time']}_{item['freq']:.2f}MHz.png", dpi=130)
        plt.close(fig)

    fig, axes = plt.subplots(
        len(times),
        len(freqs),
        figsize=(2.4 * len(freqs), 2.25 * len(times)),
        squeeze=False,
    )
    lookup = {(item["time"], item["freq"]): item for item in items}
    artist = None
    for i, time in enumerate(times):
        for j, freq in enumerate(freqs):
            ax = axes[i, j]
            item = lookup[(time, freq)]
            artist = panel(ax, np.clip(item["I"], 0, None), item["header"], 0, vmax, "inferno")
            ax.set_xticks([])
            ax.set_yticks([])
            if i == 0:
                ax.set_title(f"{freq:.2f} MHz", fontsize=9)
            if j == 0:
                ax.set_ylabel(
                    f"{time[8:10]}:{time[10:12]}:{time[12:14]}",
                    fontsize=9,
                )
    fig.suptitle("Stokes I, zoomed to ±40 arcmin", fontsize=12)
    fig.tight_layout(rect=(0, 0, 0.92, 0.96))
    cax = fig.add_axes([0.93, 0.15, 0.015, 0.7])
    fig.colorbar(artist, cax=cax, label="Jy/beam")
    fig.savefig(out / "stokes_I_montage.png", dpi=150)
    plt.close(fig)

    best = max(items, key=lambda item: float(np.nanmax(item["I"])))
    fig, axes = plt.subplots(1, 4, figsize=(14, 3.8))
    for k, (name, ax) in enumerate(zip("IQUV", axes)):
        plane = best["data"][k]
        if k == 0:
            artist = panel(
                ax,
                np.clip(plane, 0, None),
                best["header"],
                0,
                float(np.nanpercentile(plane, 99.5)),
                "inferno",
            )
        else:
            lim = float(np.nanpercentile(np.abs(plane), 99.5))
            artist = panel(ax, plane, best["header"], -lim, lim, "coolwarm")
        fig.colorbar(artist, ax=ax, fraction=0.046, pad=0.04)
        ax.set_title(name)
        ax.set_xlabel("arcmin")
        if k == 0:
            ax.set_ylabel("arcmin")
    clock = f"{best['time'][8:10]}:{best['time'][10:12]}:{best['time'][12:14]}"
    fig.suptitle(
        f"IQUV  {clock} UTC  {best['freq']:.2f} MHz  "
        f"(peak Stokes I {np.nanmax(best['I']):.0f} Jy/beam)"
    )
    fig.tight_layout()
    fig.savefig(out / "IQUV_brightest.png", dpi=140)
    plt.close(fig)
    print(out)


if __name__ == "__main__":
    main()
