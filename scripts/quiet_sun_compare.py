"""Two quiet-Sun T_B maps side by side on one log colour scale, plus their radial profiles.

    python scripts/quiet_sun_compare.py \
        data/flare20220930/overnight/1348543720_ch107_quiet.npz:1:"03:30-03:33, PKS0408-65" \
        data/flare20220930/overnight/1348547272_2s_ch107_full_fullobs.npz:0.2:"04:27-04:32 (28 quietest 2 s), 3C444" \
        --out figures/flare20220930/quiet_sun_ch107_compare

Each argument is CUBE:QUANTILE:LABEL; frames whose peak is at or below the quantile of
all frame peaks are averaged (as in quiet_sun_check.py). T_B from Rayleigh-Jeans with
the restoring beam. The profile is the azimuthal mean outside 400" around the brightest pixel.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LogNorm
from matplotlib.patches import Circle

K_B, C = 1.380649e-23, 299792458.0
RSUN = 958.0
EXCL_R = 400.0


def tb_map(path: Path, quantile: float):
    d = np.load(path)
    imgs = d["data"][:, 0]
    nu = float(d["freqs"][0]) * 1e6
    bmaj, bmin = (float(x) for x in d["beams"][0][:2])
    peaks = np.array([np.nanmax(im) for im in imgs])
    qmap = np.nanmean(imgs[peaks <= np.quantile(peaks, quantile)], axis=0)
    omega = np.pi * np.radians(bmaj / 3600) * np.radians(bmin / 3600) / (4 * np.log(2))
    return qmap * 1e-26 * C**2 / (2 * K_B * nu**2 * omega), d["extent"], float(d["freqs"][0])


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("items", nargs=2, metavar="CUBE:QUANTILE:LABEL")
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()

    maps = []
    for item in a.items:
        path, q, label = item.split(":", 2)
        maps.append((*tb_map(Path(path), float(q)), label))
    vmax = max(np.nanmax(tb) for tb, *_ in maps) / 1e6
    fig, axs = plt.subplots(1, 3, figsize=(19, 6), layout="constrained", gridspec_kw={"width_ratios": [1, 1, 1.1]})
    for ax, (tb, ext, f, label) in zip(axs[:2], maps):
        im = ax.imshow(np.clip(tb / 1e6, 0.05, None), origin="lower", extent=ext, cmap="inferno",
                       norm=LogNorm(vmin=0.05, vmax=vmax))
        ax.add_patch(Circle((0, 0), RSUN, fill=False, color="white", lw=0.7, ls="--"))
        ax.set_xlim(-2000, 2000); ax.set_ylim(-2000, 2000); ax.set_aspect("equal")
        ax.set_xlabel("Solar X [arcsec]"); ax.set_ylabel("Solar Y [arcsec]")
        ax.set_title(f"{f:.1f} MHz, {label}", fontsize=10)
    fig.colorbar(im, ax=axs[1], fraction=0.046, label="T_B [MK], log scale")
    ax = axs[2]
    edges = np.arange(0, 2.5 * RSUN + 1, 0.1 * RSUN)
    rmid = 0.5 * (edges[:-1] + edges[1:]) / RSUN
    for tb, ext, f, label in maps:
        n = tb.shape[0]; cell = (ext[1] - ext[0]) / n
        ax1 = ext[0] + (np.arange(n) + 0.5) * cell
        X, Y = np.meshgrid(ax1, ax1); R = np.hypot(X, Y)
        sy, sx = np.unravel_index(np.nanargmax(tb), tb.shape)
        keep = np.hypot(X - X[sy, sx], Y - Y[sy, sx]) > EXCL_R
        prof = [np.nanmean(tb[(R >= r0) & (R < r1) & keep]) for r0, r1 in zip(edges[:-1], edges[1:])]
        med = np.nanmedian(tb[(R < 0.8 * RSUN) & keep])
        ax.plot(rmid, np.array(prof) / 1e6, "o-", ms=4,
                label=f"{label}: disk median {med/1e6:.2f} MK, storm peak {np.nanmax(tb)/1e6:.0f} MK")
    ax.axvline(1, color="grey", ls="--", lw=0.8)
    ax.axhspan(0.5, 1.0, color="tab:green", alpha=0.15, label="typical quiet Sun 0.5–1 MK")
    ax.set_ylim(0, 2.2)
    ax.set_xlabel("distance from disk centre [R☉]"); ax.set_ylabel("T_B [MK]")
    ax.set_title(f"azimuthal mean, storm ({EXCL_R:.0f}\" around the peak) excluded", fontsize=10)
    ax.legend(fontsize=8, loc="upper right")
    fig.suptitle("Quiet Sun at the same frequency in two observations with different calibrators (P-AIRCARS + self-cal)")
    fig.savefig(f"{a.out}.png", dpi=110, bbox_inches="tight")
    print(f"wrote {a.out}.png")


if __name__ == "__main__":
    main()
