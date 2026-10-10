"""PFSS field lines from AR 13110 over AIA, with the MWA burst centroids per channel.

    python scripts/pfss_fieldlines.py GONG.fits.gz AIA.fits CENTROIDS.json --out figures/flare20220930/pfss_ar13110

GONG synoptic magnetogram -> PFSS (sunkit-magex, source surface RSS) -> field
lines traced from a lon/lat grid around the AR at 1.05 R_sun. Open lines are
drawn in green, closed in white; only the parts in front of the disk or off
the limb are drawn. For each open line the script also reports the height at
which its Earth-view projection passes closest to the mean radio centroid.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import astropy.constants as const
import astropy.units as u
import matplotlib.pyplot as plt
import numpy as np
from astropy.coordinates import SkyCoord
from astropy.visualization import AsinhStretch, ImageNormalize
from matplotlib.patches import Circle
from sunpy.coordinates import Heliocentric, HeliographicCarrington, Helioprojective, get_earth
from sunpy.map import Map
from sunkit_magex import pfss
from sunkit_magex.pfss import tracing

from solarburst.maps import aia_hpc_cutout


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("gong", type=Path)
    p.add_argument("aia", type=Path)
    p.add_argument("centroids", type=Path)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--ar", nargs=2, type=float, default=(240.0, 158.0), help="AR position, HPC arcsec")
    p.add_argument("--rss", type=float, default=2.5)
    p.add_argument("--span", type=float, default=12.0, help="seed grid half width, deg")
    p.add_argument("--win", nargs=4, type=float, default=(-100, 900, -300, 700))
    a = p.parse_args()

    aia_map = Map(str(a.aia))
    t = aia_map.date
    earth = get_earth(t)
    hpc = Helioprojective(observer=earth, obstime=t)

    gmap = Map(str(a.gong))
    gmap = gmap.resample([360, 180] * u.pix)
    out = pfss.pfss(pfss.Input(gmap, 50, a.rss))

    ar = SkyCoord(a.ar[0] * u.arcsec, a.ar[1] * u.arcsec, frame=hpc).transform_to(
        HeliographicCarrington(observer=earth, obstime=t))
    lons = np.linspace(-a.span, a.span, 13) + ar.lon.deg
    lats = np.linspace(-a.span, a.span, 13) + ar.lat.deg
    LON, LAT = np.meshgrid(lons, lats)
    seeds = SkyCoord(LON.ravel() * u.deg, LAT.ravel() * u.deg, 1.05 * const.R_sun,
                     frame=gmap.coordinate_frame)
    lines = tracing.PerformanceTracer().trace(seeds, out)

    rows = [r for r in json.load(open(a.centroids)) if r["snr"] > 50 and r["rho"] < 600]
    cx = np.array([r["x"] for r in rows]); cy = np.array([r["y"] for r in rows])
    mx, my = cx.mean(), cy.mean()

    img, aext = aia_hpc_cutout(a.aia, fov_arcsec=1300.0)
    img = img / aia_map.exposure_time.to_value(u.s)
    fig, ax = plt.subplots(figsize=(8.5, 8.5))
    win = a.win
    ny, nx = img.shape
    cols = ((np.array(win[:2]) - aext[0]) / (aext[1] - aext[0]) * nx).astype(int).clip(0, nx)
    rws = ((np.array(win[2:]) - aext[2]) / (aext[3] - aext[2]) * ny).astype(int).clip(0, ny)
    vmax = np.nanpercentile(img[rws[0]:rws[1], cols[0]:cols[1]], 99.8)
    ax.imshow(img, origin="lower", extent=aext, cmap=f"sdoaia{int(aia_map.wavelength.value)}",
              norm=ImageNormalize(vmin=0, vmax=vmax, stretch=AsinhStretch(0.02)))
    rsun = (const.R_sun / earth.radius).decompose() * u.rad
    ax.add_patch(Circle((0, 0), rsun.to_value(u.arcsec), fill=False, color="white", lw=0.6, ls="--"))

    heights = []
    n_open = n_closed = 0
    for fl in lines:
        c = fl.coords
        if len(c) < 3:
            continue
        hc = c.transform_to(Heliocentric(observer=earth, obstime=t))
        pc = c.transform_to(hpc)
        x, y = pc.Tx.to_value(u.arcsec), pc.Ty.to_value(u.arcsec)
        behind = (hc.z.to_value(u.m) < 0) & (np.hypot(x, y) < rsun.to_value(u.arcsec))
        x = np.where(behind, np.nan, x); y = np.where(behind, np.nan, y)
        if fl.is_open:
            n_open += 1
            ax.plot(x, y, color="lime", lw=0.8, alpha=0.9)
            dist = np.hypot(x - mx, y - my)
            if np.isfinite(dist).any():
                j = int(np.nanargmin(dist))
                r = float(np.sqrt(hc.x[j]**2 + hc.y[j]**2 + hc.z[j]**2) / const.R_sun)
                heights.append((float(dist[j]), r))
        else:
            n_closed += 1
            ax.plot(x, y, color="white", lw=0.5, alpha=0.5)
    sc = ax.scatter(cx, cy, c=[r["freq"] for r in rows], cmap="plasma", s=40, edgecolor="k", zorder=5)
    fig.colorbar(sc, ax=ax, fraction=0.046, label="MWA centroid frequency [MHz]")
    ax.plot(*a.ar, "+", color="cyan", ms=14, mew=2)
    ax.annotate("AR 13110", a.ar, xytext=(-80, 10), textcoords="offset points", color="cyan")
    ax.set_xlim(win[0], win[1]); ax.set_ylim(win[2], win[3]); ax.set_aspect("equal")
    ax.set_xlabel("Solar X [arcsec]"); ax.set_ylabel("Solar Y [arcsec]")
    ax.set_title(f"PFSS (GONG {gmap.date.isot[:16]}, Rss {a.rss} R☉) from AR 13110: open (green) {n_open}, closed (white) {n_closed}\n"
                 f"on AIA {int(aia_map.wavelength.value)} Å {t.isot[11:19]}; MWA centroids 04:28:36–44", fontsize=9)
    fig.tight_layout()
    fig.savefig(f"{a.out}.png", dpi=120)

    near = sorted(h for h in heights if h[0] < 60)
    summary = dict(n_open=n_open, n_closed=n_closed, mean_centroid=[float(mx), float(my)],
                   open_lines_within_60arcsec=len(near),
                   r_at_closest_approach=[h[1] for h in near])
    json.dump(summary, open(f"{a.out}.json", "w"), indent=1)
    print(json.dumps(summary, indent=1))
    print(f"wrote {a.out}.png")


if __name__ == "__main__":
    main()
