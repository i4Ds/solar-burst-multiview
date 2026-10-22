#!/usr/bin/env python
"""Figure of one P-AIRCARS image (pbcor HPC FITS): ±1500 arcsec, contours at 30/50/70/90 %
of the peak, photospheric limb, Stonyhurst grid every 15 deg (Earth view at DATE-OBS),
restoring beam, and optional markers (e.g. active region, flare).

    python scripts/event_figure.py IMAGE.fits OUT.png --title "..." \
        --mark "5.7,-188.1,AR 13932 (HMI SHARP, 04:00)" --mark "-88,-297,STIX flare"
"""
import argparse

import astropy.units as u
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from astropy.coordinates import SkyCoord
from astropy.io import fits
from matplotlib.patches import Circle, Ellipse
from sunpy.coordinates import frames, get_earth

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("fits")
ap.add_argument("out")
ap.add_argument("--title", default="")
ap.add_argument("--mark", action="append", default=[], help="x,y,label in arcsec (Earth view)")
ap.add_argument("--dpi", type=int, default=110)
a = ap.parse_args()

h = fits.getheader(a.fits)
d = np.squeeze(fits.getdata(a.fits)).astype(float)
while d.ndim > 2:          # first Stokes / frequency plane
    d = d[0]
d = np.nan_to_num(d, nan=0.0)   # blank pixels outside the field, for display only
s = 3600.0 if h.get("CUNIT1", "deg").strip().lower().startswith("deg") else 1.0
x = ((np.arange(d.shape[1]) - (h["CRPIX1"] - 1)) * h["CDELT1"] + h["CRVAL1"]) * s
y = ((np.arange(d.shape[0]) - (h["CRPIX2"] - 1)) * h["CDELT2"] + h["CRVAL2"]) * s

fig, ax = plt.subplots(figsize=(6.2, 5.6), constrained_layout=True)
im = ax.pcolormesh(x, y, d / 1e3, cmap="inferno", shading="nearest", vmin=0)
fig.colorbar(im, ax=ax, label="kJy/beam")
ax.contour(x, y, d, levels=d.max() * np.array([0.3, 0.5, 0.7, 0.9]), colors="w", linewidths=0.6)

t_obs = h["DATE-OBS"]
earth = get_earth(t_obs)
hpc = frames.Helioprojective(observer=earth, obstime=t_obs)
for kind, values in (("lon", np.arange(-90, 91, 15)), ("lat", np.arange(-75, 76, 15))):
    for v in values:
        t = np.linspace(-90, 90, 181)
        lon, lat = (np.full_like(t, v), t) if kind == "lon" else (t, np.full_like(t, v))
        c = SkyCoord(lon * u.deg, lat * u.deg, frame=frames.HeliographicStonyhurst, obstime=t_obs).transform_to(hpc)
        front = c.distance < earth.radius          # nearer than Sun centre: visible hemisphere
        ax.plot(np.where(front, c.Tx.arcsec, np.nan), np.where(front, c.Ty.arcsec, np.nan),
                color="w", lw=0.9 if v == 0 else 0.4, alpha=0.45)
limb = 959.6 * u.AU.to(u.m) / earth.radius.to(u.m).value   # photospheric radius, arcsec
ax.add_patch(Circle((0, 0), limb, fill=False, ec="w", lw=0.8))
ax.add_patch(Ellipse((-1250, -1250), h["BMAJ"] * 3600, h["BMIN"] * 3600, angle=90 + h.get("BPA", 0),
                     fill=False, ec="c", lw=1))
for m, (sym, col) in zip(a.mark, [("x", "lime"), ("+", "c"), ("^", "w"), ("s", "y")]):
    mx, my, label = m.split(",", 2)
    ax.plot(float(mx), float(my), sym, color=col, ms=11, mew=2, label=label)
ax.set_xlim(-1500, 1500); ax.set_ylim(-1500, 1500); ax.set_aspect("equal")
ax.set_xlabel("Solar X (arcsec)"); ax.set_ylabel("Solar Y (arcsec)")
ax.set_title((a.title + "\n" if a.title else "") +
             "contours 30/50/70/90 % of peak; Stonyhurst grid every 15°", fontsize=9, loc="left")
if a.mark:
    ax.legend(loc="upper right", fontsize=8)
fig.savefig(a.out, dpi=a.dpi)
