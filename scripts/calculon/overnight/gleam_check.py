"""Astrometry check of a wide-field MWA image against the GGSM sky model (GLEAM-based).

Finds compact peaks above SNR x local rms, matches them to GGSM sources whose
predicted flux at the image frequency exceeds MIN_FLUX, and reports the
median position offset (image minus catalogue). 3C273 and Virgo A are
reported separately. With --sun, peaks within EXCLUDE_DEG of the Sun are
ignored (Sun position from GCRS, not ICRS, which is barycentric).

    python3 gleam_check.py IMAGE.fits GGSM.fits OUT_PREFIX [--sun] [--snr 7]

Runs in the calculon container (numpy, scipy, astropy, matplotlib).
"""

import argparse
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import astropy.units as u
from astropy.coordinates import SkyCoord, get_body
from astropy.io import fits
from astropy.table import Table
from astropy.time import Time
from astropy.wcs import WCS
from scipy.ndimage import maximum_filter

NAMED = {"3C273": (187.27792, 2.05239), "Virgo A (M87)": (187.70593, 12.39112)}


def local_rms(img, tile=128):
    ny, nx = img.shape
    out = np.empty_like(img)
    for y in range(0, ny, tile):
        for x in range(0, nx, tile):
            t = img[y:y + tile, x:x + tile]
            t = t[np.isfinite(t)]
            out[y:y + tile, x:x + tile] = 1.4826 * np.median(np.abs(t - np.median(t))) if t.size > 50 else np.nan
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("image")
    p.add_argument("ggsm")
    p.add_argument("out")
    p.add_argument("--sun", action="store_true")
    p.add_argument("--exclude-deg", type=float, default=2.5)
    p.add_argument("--snr", type=float, default=7.0)
    p.add_argument("--min-flux", type=float, default=3.0, help="predicted Jy at image frequency")
    p.add_argument("--match-arcmin", type=float, default=2.0)
    p.add_argument("--radius-deg", type=float, default=17.0)
    a = p.parse_args()

    with fits.open(a.image) as h:
        img = np.squeeze(h[0].data).astype(float)
        hd = h[0].header
    wcs = WCS(hd).celestial
    freq = float(hd["CRVAL3"]) / 1e6
    centre = SkyCoord(hd["CRVAL1"] * u.deg, hd["CRVAL2"] * u.deg)

    rms = local_rms(img)
    peaks = (img == maximum_filter(img, size=9)) & (img > a.snr * rms) & np.isfinite(rms)
    yy, xx = np.nonzero(peaks)
    det = wcs.pixel_to_world(xx, yy)
    snr = img[yy, xx] / rms[yy, xx]
    keep = centre.separation(det).deg < a.radius_deg
    sun = None
    if a.sun:
        g = get_body("sun", Time(hd["DATE-OBS"]))
        sun = SkyCoord(g.ra, g.dec)
        keep &= sun.separation(det).deg > a.exclude_deg
    det, snr, peakval = det[keep], snr[keep], img[yy, xx][keep]

    cat = Table.read(a.ggsm)
    r = np.log(freq / 200.0)
    spred = np.asarray(cat["S_200"]) * np.exp(np.asarray(cat["alpha"]) * r + np.asarray(cat["beta"]) * r * r)
    cc = SkyCoord(np.asarray(cat["RAJ2000"]) * u.deg, np.asarray(cat["DEJ2000"]) * u.deg)
    sel = (spred > a.min_flux) & (centre.separation(cc).deg < a.radius_deg)
    if sun is not None:
        sel &= sun.separation(cc).deg > a.exclude_deg
    cc, spred, names = cc[sel], spred[sel], np.asarray(cat["Name"])[sel]

    rows = []
    if len(det) and len(cc):
        idx, sep, _ = det.match_to_catalog_sky(cc)
        for k in np.flatnonzero(sep.arcmin < a.match_arcmin):
            c = cc[idx[k]]
            dra = ((det[k].ra - c.ra).wrap_at(180 * u.deg) * np.cos(c.dec)).to_value(u.arcsec)
            ddec = (det[k].dec - c.dec).to_value(u.arcsec)
            rows.append(dict(name=str(names[idx[k]]), ra=c.ra.deg, dec=c.dec.deg, dra=dra, ddec=ddec,
                             snr=float(snr[k]), s_pred=float(spred[idx[k]]), peak=float(peakval[k])))
    named = {}
    for nm, (ra, dec) in NAMED.items():
        c = SkyCoord(ra * u.deg, dec * u.deg)
        px, py = wcs.world_to_pixel(c)
        ix, iy = int(round(float(px))), int(round(float(py)))
        if 10 <= ix < img.shape[1] - 10 and 10 <= iy < img.shape[0] - 10:
            box = img[iy - 10:iy + 11, ix - 10:ix + 11]
            jy, jx = np.unravel_index(np.nanargmax(box), box.shape)
            m = wcs.pixel_to_world(ix - 10 + jx, iy - 10 + jy)
            named[nm] = dict(dra=float(((m.ra - c.ra).wrap_at(180 * u.deg) * np.cos(c.dec)).to_value(u.arcsec)),
                             ddec=float((m.dec - c.dec).to_value(u.arcsec)),
                             snr=float(img[iy - 10 + jy, ix - 10 + jx] / rms[iy - 10 + jy, ix - 10 + jx]),
                             dist_from_sun_deg=float(sun.separation(c).deg) if sun is not None else None)

    dra = np.array([r_["dra"] for r_ in rows])
    ddec = np.array([r_["ddec"] for r_ in rows])
    summary = dict(image=a.image, freq_mhz=freq, date_obs=hd["DATE-OBS"], n_detections=int(len(det)),
                   n_catalogue=int(len(cc)), n_matched=len(rows),
                   median_dra_arcsec=float(np.median(dra)) if len(rows) else None,
                   median_ddec_arcsec=float(np.median(ddec)) if len(rows) else None,
                   mad_dra_arcsec=float(1.4826 * np.median(np.abs(dra - np.median(dra)))) if len(rows) else None,
                   mad_ddec_arcsec=float(1.4826 * np.median(np.abs(ddec - np.median(ddec)))) if len(rows) else None,
                   named=named, beam_arcsec=[hd.get("BMAJ", 0) * 3600, hd.get("BMIN", 0) * 3600])
    with open(a.out + ".json", "w") as f:
        json.dump(dict(summary=summary, matches=rows), f, indent=1)

    fig, axs = plt.subplots(1, 2, figsize=(12, 5.5))
    if len(rows):
        axs[0].scatter(dra, ddec, c=[r_["snr"] for r_ in rows], cmap="viridis", s=12)
        axs[0].axhline(0, c="grey", lw=0.5); axs[0].axvline(0, c="grey", lw=0.5)
        axs[0].plot(np.median(dra), np.median(ddec), "r+", ms=14, mew=2)
        ra_ = np.array([r_["ra"] for r_ in rows]); de_ = np.array([r_["dec"] for r_ in rows])
        axs[1].quiver(ra_, de_, dra, ddec, angles="xy", scale_units="xy", scale=60, width=0.003)
        axs[1].invert_xaxis()
    if sun is not None:
        axs[1].plot(sun.ra.deg, sun.dec.deg, "o", c="orange", ms=14)
    axs[0].set_xlabel("ΔRA cosδ [arcsec]"); axs[0].set_ylabel("ΔDec [arcsec]")
    axs[0].set_title(f"{len(rows)} matches, median ({summary['median_dra_arcsec'] or 0:+.0f}″, {summary['median_ddec_arcsec'] or 0:+.0f}″)")
    axs[1].set_xlabel("RA [deg]"); axs[1].set_ylabel("Dec [deg]"); axs[1].set_title("offset vectors (1° = 60″)")
    fig.suptitle(f"{a.image.split('/')[-1]}  {freq:.1f} MHz  {hd['DATE-OBS'][:19]}")
    fig.tight_layout(); fig.savefig(a.out + ".png", dpi=110)
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
