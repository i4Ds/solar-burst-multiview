#!/usr/bin/env python
"""MWA image contours over AIA 193 A, with NOAA active regions and PFSS field lines.

    python scripts/euv_context.py IMAGE.fits --out OUT.png --cache DIR

For the time of the MWA image (DATE-OBS of a P-AIRCARS pbcor HPC FITS):
  - AIA 193 A synoptic image (1024 px, 2 min cadence, public JSOC directory; the VSO level-1
    download from nascom timed out and a JSOC export needs a registered e-mail), nearest
    in time, cached in DIR;
  - GONG synoptic magnetogram nearest in time, PFSS (sunkit-magex, source surface Rss),
    field lines traced from a seed grid around every NOAA region on the disk (HEK: HMI SHARP
    centroid nearest in time, else the SWPC report, rotated to the image time)
    at 1.05 R_sun: open green, closed white, only the parts in front of the disk or off the
    limb; the PFSS solution is cached in DIR as the traced lines (same for all images of
    an event);
  - MWA Stokes I contours at 30/50/70/90 % of the image peak, restoring beam, optical limb.
The field of view is +-1500 arcsec (Earth view). Seeds and lines follow
scripts/pfss_fieldlines.py (2022-09-30), generalised to all regions.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import astropy.constants as const
import astropy.units as u
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import sunpy.visualization.colormaps  # noqa: F401  registers the sdoaia colour maps
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.time import Time
from astropy.visualization import AsinhStretch, ImageNormalize
from matplotlib.patches import Circle, Ellipse
from sunpy.coordinates import Heliocentric, HeliographicCarrington, HeliographicStonyhurst, Helioprojective, get_earth
from sunpy.map import Map

HALF = 1500.0


def fetch(query_attrs, cache: Path, prefix: str) -> Path | None:
    """First file of a Fido search, cached under cache/prefix*."""
    have = sorted(cache.glob(prefix + "*"))
    if have:
        return have[0]
    from sunpy.net import Fido
    res = Fido.search(*query_attrs)
    if not len(res) or not len(res[0]):
        return None
    files = Fido.fetch(res[0][:1], path=str(cache / (prefix + "_{file}")), progress=False)
    return Path(files[0]) if files else None


def aia_synoptic(t: Time, cache: Path, wave: int = 193) -> Path | None:
    """Nearest AIA synoptic image (http://jsoc.stanford.edu/data/aia/synoptic/), cached."""
    import urllib.request
    base = Time(round(t.unix / 120) * 120, format="unix")
    for dm in (0, 2, -2, 4, -4):
        tt = Time(base.unix + dm * 60, format="unix")
        name = f"AIA{tt.strftime('%Y%m%d_%H%M')}_{wave:04d}.fits"
        f = cache / name
        if f.exists() and f.stat().st_size > 100000:
            return f
        url = f"http://jsoc.stanford.edu/data/aia/synoptic/{tt.strftime('%Y/%m/%d')}/H{tt.strftime('%H')}00/{name}"
        try:
            with urllib.request.urlopen(url, timeout=90) as r:
                f.write_bytes(r.read())
            if f.stat().st_size > 100000:
                return f
        except Exception:
            pass
    return None


def noaa_regions(t: Time, cache: Path) -> list[dict]:
    f = cache / "noaa_regions.json"
    if f.exists():
        return json.loads(f.read_text())
    from sunpy.net import Fido
    from sunpy.net import attrs as a
    res = Fido.search(a.Time(t - 12 * u.hour, t + 12 * u.hour), a.hek.EventType("AR"))
    # one SWPC report per region, the one nearest in time, rotated to t (13.2 deg/day synodic);
    # the +-12 h window also returns the previous day's reports, 13 deg further east
    # HMI SHARP (magnetic centroid, 4 h cadence) is preferred: SWPC can list a region twice
    # with positions 10 deg apart (13932 on 2024-12-25)
    best = {}
    for r in res["hek"] if len(res) else []:
        n = int(r["ar_noaanum"] or 0)
        frm = str(r["frm_name"])
        if not n or frm not in ("HMI SHARP", "NOAA SWPC Observer"):
            continue
        dt = (t - Time(str(r["event_starttime"]))).to_value(u.day)
        rank = (0 if frm == "HMI SHARP" else 1, abs(dt))
        if n not in best or rank < best[n][0]:
            best[n] = (rank, dt, float(r["hgs_x"]), float(r["hgs_y"]), frm)
    out = [dict(noaa=n, hgs_lon=round(lon + 13.2 * dt, 2), hgs_lat=lat, obs=t.isot, source=frm)
           for n, (_, dt, lon, lat, frm) in sorted(best.items())]
    f.write_text(json.dumps(out))
    return out


def pfss_lines(t: Time, regions: list[dict], cache: Path, rss: float, span: float) -> list[dict]:
    """Field lines as Stonyhurst-independent 3D coordinates (HGC lon, lat, r), cached."""
    f = cache / "pfss_lines.json"
    if f.exists():
        return json.loads(f.read_text())
    from sunkit_magex import pfss
    from sunkit_magex.pfss import tracing
    from sunpy.net import attrs as a
    g = fetch([a.Time(t - 3 * u.hour, t + 3 * u.hour), a.Instrument("GONG")], cache, "gong")
    if g is None:
        return []
    gmap = Map(str(g)).resample([360, 180] * u.pix)
    out = pfss.pfss(pfss.Input(gmap, 50, rss))
    earth = get_earth(t)
    seeds = []
    for reg in regions:
        c = SkyCoord(reg["hgs_lon"] * u.deg, reg["hgs_lat"] * u.deg, frame=HeliographicStonyhurst, obstime=t)
        c = c.transform_to(HeliographicCarrington(observer=earth, obstime=t))
        for dl in np.linspace(-span, span, 7):
            for db in np.linspace(-span, span, 7):
                seeds.append((c.lon.deg + dl, c.lat.deg + db))
    if not seeds:
        return []
    s = np.array(seeds)
    seed = SkyCoord(s[:, 0] * u.deg, s[:, 1] * u.deg, 1.05 * const.R_sun, frame=gmap.coordinate_frame)
    lines = tracing.PerformanceTracer().trace(seed, out)
    res = []
    for fl in lines:
        c = fl.coords
        if len(c) < 3:
            continue
        c = c.transform_to(HeliographicCarrington(observer=earth, obstime=t))
        res.append(dict(open=bool(fl.is_open), lon=c.lon.deg.round(3).tolist(), lat=c.lat.deg.round(3).tolist(),
                        r=(c.radius / const.R_sun).decompose().value.round(4).tolist()))
    f.write_text(json.dumps(dict(gong=str(gmap.date.isot), rss=rss, lines=res)))
    return json.loads(f.read_text())


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("fits", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--cache", type=Path, required=True, help="per-event cache (AIA, GONG, PFSS lines, regions)")
    ap.add_argument("--rss", type=float, default=2.5)
    ap.add_argument("--span", type=float, default=8.0, help="seed grid half width around each region, deg")
    ap.add_argument("--title", default="")
    a = ap.parse_args()
    a.cache.mkdir(parents=True, exist_ok=True)

    h = fits.getheader(a.fits)
    d = np.squeeze(fits.getdata(a.fits)).astype(float)
    while d.ndim > 2:
        d = d[0]
    s = 3600.0 if h.get("CUNIT1", "deg").strip().lower().startswith("deg") else 1.0
    mx = ((np.arange(d.shape[1]) - (h["CRPIX1"] - 1)) * h["CDELT1"] + h["CRVAL1"]) * s
    my = ((np.arange(d.shape[0]) - (h["CRPIX2"] - 1)) * h["CDELT2"] + h["CRVAL2"]) * s
    t = Time(h["DATE-OBS"])
    earth = get_earth(t)
    hpc = Helioprojective(observer=earth, obstime=t)
    nu = next((h[f"CRVAL{k}"] for k in range(1, 5) if str(h.get(f"CTYPE{k}", "")).startswith("FREQ")), np.nan) / 1e6

    aia = aia_synoptic(t, a.cache)
    fig, ax = plt.subplots(figsize=(7.4, 7.0))
    if aia is not None:
        am = Map(str(aia))
        cut = am.submap(SkyCoord(-HALF * 1.05 * u.arcsec, -HALF * 1.05 * u.arcsec, frame=am.coordinate_frame),
                        top_right=SkyCoord(HALF * 1.05 * u.arcsec, HALF * 1.05 * u.arcsec, frame=am.coordinate_frame))
        cut = cut.resample([1024, 1024] * u.pix)
        img = cut.data
        bl, tr = cut.bottom_left_coord, cut.top_right_coord
        ext = [bl.Tx.to_value(u.arcsec), tr.Tx.to_value(u.arcsec), bl.Ty.to_value(u.arcsec), tr.Ty.to_value(u.arcsec)]
        ax.imshow(img, origin="lower", extent=ext, cmap="sdoaia193",
                  norm=ImageNormalize(vmin=0, vmax=np.nanpercentile(img, 99.7), stretch=AsinhStretch(0.02)))
        aia_label = f"AIA 193 Å {am.date.isot[11:19]} (synoptic)"
    else:
        ax.set_facecolor("black")
        aia_label = "no AIA 193 Å image found"

    regions = noaa_regions(t, a.cache)
    pf = pfss_lines(t, regions, a.cache, a.rss, a.span)
    n_open = n_closed = 0
    rsun = (const.R_sun / earth.radius).decompose().value * 206264.806
    for fl in (pf.get("lines", []) if isinstance(pf, dict) else []):
        c = SkyCoord(np.array(fl["lon"]) * u.deg, np.array(fl["lat"]) * u.deg, np.array(fl["r"]) * const.R_sun,
                     frame=HeliographicCarrington(observer=earth, obstime=t))
        hc = c.transform_to(Heliocentric(observer=earth, obstime=t))
        pc = c.transform_to(hpc)
        x, y = pc.Tx.to_value(u.arcsec), pc.Ty.to_value(u.arcsec)
        behind = (hc.z.to_value(u.m) < 0) & (np.hypot(x, y) < rsun)
        x = np.where(behind, np.nan, x); y = np.where(behind, np.nan, y)
        if fl["open"]:
            n_open += 1
            ax.plot(x, y, color="lime", lw=0.7, alpha=0.85)
        else:
            n_closed += 1
            ax.plot(x, y, color="white", lw=0.4, alpha=0.45)
    for reg in regions:
        c = SkyCoord(reg["hgs_lon"] * u.deg, reg["hgs_lat"] * u.deg, frame=HeliographicStonyhurst,
                     obstime=Time(reg["obs"])).transform_to(hpc)
        if np.hypot(c.Tx.to_value(u.arcsec), c.Ty.to_value(u.arcsec)) < rsun:
            ax.annotate(f"{reg['noaa']}", (c.Tx.to_value(u.arcsec), c.Ty.to_value(u.arcsec)), color="#ffd166",
                        fontsize=8, ha="center", va="center", fontweight="bold")
    pk = np.nanmax(d)
    ax.contour(mx, my, np.nan_to_num(d), levels=pk * np.array([0.3, 0.5, 0.7, 0.9]), colors="cyan",
               linewidths=[0.7, 0.9, 1.1, 1.4])
    ax.add_patch(Circle((0, 0), rsun, fill=False, color="white", lw=0.6, ls="--"))
    ax.add_patch(Ellipse((-1300, -1300), h["BMAJ"] * 3600, h["BMIN"] * 3600, angle=90 + h.get("BPA", 0),
                         fill=False, ec="cyan", lw=1))
    ax.set_xlim(-HALF, HALF); ax.set_ylim(-HALF, HALF); ax.set_aspect("equal")
    ax.set_xlabel("Solar X [arcsec]"); ax.set_ylabel("Solar Y [arcsec]")
    gong = pf.get("gong", "")[:16] if isinstance(pf, dict) else ""
    ax.set_title((a.title + "\n" if a.title else "") +
                 f"MWA {nu:.1f} MHz {t.isot[11:21]} (cyan, 30/50/70/90 %) on {aia_label}\n"
                 f"PFSS {('GONG ' + gong) if gong else 'n/a'}, Rss {a.rss}: open {n_open} (green), closed {n_closed}; "
                 f"NOAA regions (yellow)", fontsize=8.5, loc="left")
    fig.tight_layout()
    a.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(a.out, dpi=110)
    print(f"wrote {a.out}: {len(regions)} regions, {n_open} open, {n_closed} closed lines")


if __name__ == "__main__":
    main()
