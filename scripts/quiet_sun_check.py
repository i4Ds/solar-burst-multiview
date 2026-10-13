"""Quiet-Sun map from a P-AIRCARS image series, as a calibration check.

    python scripts/quiet_sun_check.py data/flare20220930/overnight/1348547272_2s_ch116_quiet.npz \
        data/flare20220930/aia/aia.lev1.193A_2022_09_30T04_28_40.84Z.image_lev1.fits \
        --out figures/flare20220930/quiet_sun_ch116

Frames whose peak is at or below the --quantile of all peaks (default: the median) are averaged (this drops the short
noise-storm spikes). The map is converted to brightness temperature with the
Rayleigh-Jeans relation and the restoring beam. A circle of EXCL_R arcsec around
the brightest pixel (the noise storm) is excluded from the quiet-disk numbers.

Checks printed and written to <out>.json:
  * centre of the quiet emission (should be close to disk centre);
  * azimuthal T_B profile (outside the storm) and the radius where it falls to
    half of the 0.7-1.0 R_sun plateau (the radio Sun is larger than the optical disk);
  * median T_B of the quiet disk (r < 0.8 R_sun), expected ~0.5-1 MK at 100-200 MHz;
  * total flux within 2 R_sun and the flux without the storm, against a
    uniform 1.1 R_sun disk at 0.5 and 1 MK.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import astropy.units as u
import matplotlib.pyplot as plt
import numpy as np
from astropy.visualization import AsinhStretch, ImageNormalize
from matplotlib.colors import LogNorm
from matplotlib.patches import Circle
from sunpy.map import Map

from solarburst.maps import aia_hpc_cutout

K_B, C = 1.380649e-23, 299792458.0
RSUN = 958.0


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("cube", type=Path)
    p.add_argument("aia", type=Path)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--excl-r", type=float, default=400.0)
    p.add_argument("--compare", action="append", default=[], metavar="LABEL:X:Y",
                   help="positions to mark, e.g. 'burst 04:28:31:320:100'")
    p.add_argument("--quantile", type=float, default=0.5,
                   help="keep frames whose peak is at or below this quantile of all peaks")
    p.add_argument("--cal", default="3C444", help="calibrator name for the title")
    p.add_argument("--frame", default="2 s", help="frame duration for the title")
    a = p.parse_args()

    d = np.load(a.cube)
    cube, freqs, times, ext, beams = d["data"], d["freqs"], d["times"], d["extent"], d["beams"]
    imgs = cube[:, 0]
    nu = float(freqs[0]) * 1e6
    bmaj, bmin = float(beams[0][0]), float(beams[0][1])
    peaks = np.array([np.nanmax(im) for im in imgs])
    quiet = peaks <= np.quantile(peaks, a.quantile)
    qmap = np.nanmean(imgs[quiet], axis=0)

    n = qmap.shape[0]
    cell = (ext[1] - ext[0]) / n
    ax1 = ext[0] + (np.arange(n) + 0.5) * cell
    X, Y = np.meshgrid(ax1, ax1)
    R = np.hypot(X, Y)
    omega_beam = np.pi * np.radians(bmaj / 3600) * np.radians(bmin / 3600) / (4 * np.log(2))
    tb = qmap * 1e-26 * C**2 / (2 * K_B * nu**2 * omega_beam)
    beam_px = np.pi * bmaj * bmin / (4 * np.log(2)) / cell**2

    j = np.nanargmax(qmap); sy, sx = np.unravel_index(j, qmap.shape)
    storm_xy = (float(X[sy, sx]), float(Y[sy, sx]))
    m50 = (qmap > 0.5 * qmap[sy, sx]) & (np.hypot(X - storm_xy[0], Y - storm_xy[1]) < a.excl_r)
    storm_c = (float((qmap[m50] * X[m50]).sum() / qmap[m50].sum()), float((qmap[m50] * Y[m50]).sum() / qmap[m50].sum()))
    not_storm = np.hypot(X - storm_xy[0], Y - storm_xy[1]) > a.excl_r

    wq = np.clip(qmap, 0, None) * not_storm * (R < 1.6 * RSUN)
    centre = (float((wq * X).sum() / wq.sum()), float((wq * Y).sum() / wq.sum()))
    edges = np.arange(0, 2.5 * RSUN + 1, 0.1 * RSUN)
    prof = np.array([np.nanmean(tb[(R >= r0) & (R < r1) & not_storm]) for r0, r1 in zip(edges[:-1], edges[1:])])
    rmid = 0.5 * (edges[:-1] + edges[1:])
    # Edge of the radio disk: where the profile falls below half of the quiet-disk
    # plateau (0.7-1.0 R_sun); the inner rings still catch the edge of the storm.
    plateau = np.nanmedian(prof[(rmid > 0.7 * RSUN) & (rmid < RSUN)])
    below = np.flatnonzero((rmid > RSUN) & (prof < 0.5 * plateau))
    r_half = float(rmid[below[0]] / RSUN) if below.size else None
    tb_quiet = float(np.nanmedian(tb[(R < 0.8 * RSUN) & not_storm]))
    s_tot = float(np.nansum(qmap[R < 2 * RSUN]) / beam_px)
    s_nostorm = float(np.nansum(qmap[(R < 2 * RSUN) & not_storm]) / beam_px)
    omega_disk = np.pi * np.radians(1.1 * RSUN / 3600) ** 2
    s_exp = [2 * K_B * nu**2 / C**2 * t * omega_disk / 1e-26 for t in (0.5e6, 1.0e6)]
    summary = dict(freq_mhz=float(freqs[0]), frames_total=int(len(imgs)), frames_quiet=int(quiet.sum()),
                   times_quiet=[str(t) for t in np.array(times)[quiet]], beam_arcsec=[bmaj, bmin],
                   quiet_centre_arcsec=centre, radio_half_radius_rsun=r_half,
                   tb_quiet_disk_MK=tb_quiet / 1e6, s_total_jy=s_tot, s_without_storm_jy=s_nostorm,
                   s_expected_1p1rsun_0p5_1MK_jy=s_exp, storm_peak_xy=storm_xy, storm_centroid_xy=storm_c,
                   storm_peak_tb_MK=float(tb[sy, sx] / 1e6), storm_area_arcsec2_above_half=float(m50.sum() * cell**2))
    json.dump(summary, open(f"{a.out}.json", "w"), indent=1)
    print(json.dumps(summary, indent=1))

    smap = Map(str(a.aia))
    aia, aext = aia_hpc_cutout(a.aia, fov_arcsec=1300.0)
    aia = aia / smap.exposure_time.to_value(u.s)
    fig, axs = plt.subplots(2, 2, figsize=(13, 12))
    ax = axs[0, 0]
    # Log scale: the noise storm is ~100x brighter than the quiet disk.
    im = ax.imshow(np.clip(tb / 1e6, 0.05, None), origin="lower", extent=ext, cmap="inferno",
                   norm=LogNorm(vmin=0.05, vmax=np.nanmax(tb) / 1e6))
    fig.colorbar(im, ax=ax, fraction=0.046, label="T_B [MK], log scale")
    ax.set_title(f"MWA {freqs[0]:.1f} MHz, mean of {quiet.sum()} quiet {a.frame} frame(s)")
    ax = axs[0, 1]
    ax.imshow(aia, origin="lower", extent=aext, cmap=f"sdoaia{int(smap.wavelength.value)}",
              norm=ImageNormalize(vmin=0, vmax=np.nanpercentile(aia, 99.8), stretch=AsinhStretch(0.02)))
    lev = [0.5e6, 1e6, 2e6, 5e6, 1e7, 3e7, 1e8]
    cs = ax.contour(tb, levels=[l for l in lev if l < np.nanmax(tb)], extent=ext, origin="lower", colors="cyan", linewidths=0.8)
    ax.clabel(cs, fmt=lambda v: f"{v/1e6:g} MK", fontsize=7)
    ax.set_title(f"T_B contours on AIA {int(smap.wavelength.value)} Å")
    for ax in axs[0]:
        ax.add_patch(Circle((0, 0), RSUN, fill=False, color="white", lw=0.7, ls="--"))
        ax.add_patch(Circle(storm_xy, a.excl_r, fill=False, color="lime", lw=0.7, ls=":"))
        ax.plot(*centre, "c+", ms=14, mew=2)
        for item in a.compare:
            lab, x, y = item.rsplit(":", 2)
            ax.plot(float(x), float(y), "x", color="magenta", ms=10, mew=2)
            ax.annotate(lab, (float(x), float(y)), xytext=(6, -12), textcoords="offset points", color="magenta", fontsize=8)
        ax.set_xlim(-2000, 2000); ax.set_ylim(-2000, 2000); ax.set_aspect("equal")
        ax.set_xlabel("Solar X [arcsec]"); ax.set_ylabel("Solar Y [arcsec]")
    ax = axs[1, 0]
    ax.plot(rmid / RSUN, prof / 1e6, "o-", label="azimuthal mean, storm excluded")
    ax.axvline(1, color="grey", ls="--", label="optical limb")
    ax.axhspan(0.5, 1.0, color="tab:green", alpha=0.2, label="typical quiet Sun 0.5–1 MK")
    if r_half:
        ax.axvline(r_half, color="tab:red", ls=":", label=f"half of the 0.7–1.0 R☉ plateau at {r_half:.2f} R☉")
    ax.set_xlabel("distance from disk centre [R☉]"); ax.set_ylabel("T_B [MK]"); ax.legend(fontsize=8)
    ax.set_title(f"quiet-disk median {tb_quiet/1e6:.2f} MK; flux {s_tot:.3g} Jy (without storm {s_nostorm:.3g})")
    ax = axs[1, 1]
    ax.plot(range(len(times)), peaks / 1e5, "o-", color="grey")
    ax.plot(np.flatnonzero(quiet), peaks[quiet] / 1e5, "o", color="tab:blue", label=f"used (≤ {a.quantile:g} quantile)")
    tick = list(range(0, len(times), max(1, len(times) // 10)))
    ax.set_xticks(tick); ax.set_xticklabels([f"{times[i][8:10]}:{times[i][10:12]}:{times[i][12:14]}" for i in tick], fontsize=8)
    ax.set_ylabel("frame peak [10⁵ Jy/beam]"); ax.legend(); ax.set_title("frame selection")
    fig.suptitle(f"Quiet-Sun check, MWA {freqs[0]:.1f} MHz (P-AIRCARS, {a.cal} + self-cal); cyan +: centre of quiet emission")
    fig.tight_layout()
    fig.savefig(f"{a.out}.png", dpi=110)
    print(f"wrote {a.out}.png")


if __name__ == "__main__":
    main()
