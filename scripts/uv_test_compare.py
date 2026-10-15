"""Short-baseline test: T_B maps of the same calibrated data imaged with all baselines
and with short baselines thinned to another array layout (uv_test.sbatch), side by side
in the style of Sharma & Oberoi (2020), plus the baseline histograms.

    python scripts/uv_test_compare.py data/quiet2015/uvtest --ref data/quiet2015/uvtest/uv_1348543720.npz \
        --out figures/quiet2015/uvtest_1133149192_ch114
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from astropy.io import fits
from matplotlib.patches import Circle, Ellipse

from solarburst.maps import radec_to_hpc

K_B, C = 1.380649e-23, 299792458.0
RSUN = 958.0


def tb_hpc(path: Path):
    with fits.open(path) as h:
        hdr, data = h[0].header, np.squeeze(h[0].data)
    nu = hdr["CRVAL3"] if "FREQ" in str(hdr.get("CTYPE3", "")) else hdr["CRVAL4"]
    bmaj, bmin, bpa = hdr["BMAJ"] * 3600, hdr["BMIN"] * 3600, hdr.get("BPA", 0.0)
    omega = np.pi * np.radians(bmaj / 3600) * np.radians(bmin / 3600) / (4 * np.log(2))
    hpc, ext = radec_to_hpc(data, hdr, fov_arcsec=2500.0)
    return hpc * 1e-26 * C**2 / (2 * K_B * nu**2 * omega) / 1e6, ext, nu, (bmaj, bmin, bpa)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("dir", type=Path, help="with all-image.fits, thin-image.fits, uv_all.npz, uv_thin.npz")
    p.add_argument("--ref", type=Path, required=True, help="uv npz of the reference layout")
    p.add_argument("--reflabel", default="2022 (Phase II Extended)")
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()

    fig, axs = plt.subplots(1, 3, figsize=(19, 5.6), layout="constrained")
    stats = {}
    for ax, v, title in zip(axs[:2], ("all", "thin"), ("all baselines", "short baselines thinned to the 2022 counts")):
        tb, ext, nu, (bmaj, bmin, bpa) = tb_hpc(a.dir / f"{v}-image.fits")
        n = tb.shape[0]; cell = (ext[1] - ext[0]) / n
        ax1 = ext[0] + (np.arange(n) + 0.5) * cell
        X, Y = np.meshgrid(ax1, ax1); R = np.hypot(X, Y)
        disk = tb[R < 0.8 * RSUN]
        stats[v] = dict(median_disk_MK=float(np.nanmedian(disk)), peak_MK=float(np.nanmax(tb)),
                        flux_2rsun_rel=float(np.nansum(tb[R < 2 * RSUN])), beam_arcsec=[bmaj, bmin])
        im = ax.imshow(np.where(tb > 0.2, tb, np.nan), origin="lower", extent=ext, cmap="jet", vmin=0, vmax=1.5)
        pk = np.nanmax(tb)
        ax.contour(tb, levels=[f * pk for f in (0.7, 0.75, 0.8, 0.85, 0.9, 0.95)], extent=ext, origin="lower",
                   colors="black", linewidths=0.8)
        for r in (1, 2):
            ax.add_patch(Circle((0, 0), r * RSUN, fill=False, color="brown", lw=2))
        ax.add_patch(Ellipse((-2000, -2000), bmin, bmaj, angle=-bpa, fill=False, color="black"))
        ax.set_xlim(-2500, 2500); ax.set_ylim(-2500, 2500); ax.set_aspect("equal"); ax.grid(ls=":", color="grey")
        ax.set_xlabel("Solar X (arcsec)"); ax.set_ylabel("Solar Y (arcsec)")
        ax.set_title(f"{nu/1e6:.1f} MHz, {title}\nquiet disk (r < 0.8 R☉) median {np.nanmedian(disk):.2f} MK, "
                     f"peak {pk:.2f} MK", fontsize=10)
    fig.colorbar(im, ax=axs[1], label="T_B (MK)")
    s = stats["thin"]["flux_2rsun_rel"] / stats["all"]["flux_2rsun_rel"]
    stats["flux_ratio_thin_over_all"] = float(s)
    ax = axs[2]
    for f, lab, kw in ((a.dir / "uv_all.npz", "2015, all", dict(color="tab:blue")),
                       (a.dir / "uv_thin.npz", "2015, thinned", dict(color="tab:orange")),
                       (a.ref, a.reflabel, dict(color="black", ls="--"))):
        d = np.load(f)
        ax.hist(d["uvl"], bins=np.logspace(0, np.log10(4000), 40), histtype="step", lw=1.6, label=lab, **kw)
    ax.set_xscale("log"); ax.set_xlabel("baseline length (wavelengths)"); ax.set_ylabel("baselines")
    ax.axvspan(1, 100, color="grey", alpha=0.12, label="scales of the whole solar disk")
    ax.legend(fontsize=8); ax.set_title(f"baseline lengths; total flux thinned/all = {s:.2f}", fontsize=10)
    fig.suptitle("Short-baseline test on the 2015-12-03 quiet Sun (Sharma & Oberoi 2020), same calibration, same wsclean settings")
    a.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(f"{a.out}.png", dpi=110)
    json.dump(stats, open(f"{a.out}.json", "w"), indent=1)
    print(json.dumps(stats, indent=1))


if __name__ == "__main__":
    main()
