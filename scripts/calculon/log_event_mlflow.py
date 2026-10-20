#!/usr/bin/env python3
"""Log one archive-burst image to MLflow (experiment "archive-bursts").

Reads what event_image.sh leaves behind: the window chosen from the MWA light curve
(peak.txt), the P-AIRCARS image(s) in pbcor_hpcs, the light-curve PNG and the
P-AIRCARS montage, and logs one run per image with
  params:    obsid, calibrator, channel, frequency, window, image time resolution,
             pipeline settings, git commit of solar-burst-multiview
  metrics:   peak (Jy/beam), off-Sun rms, peak/rms, half-max centroid (arcsec, R_sun),
             beam, Rayleigh-Jeans T_B of the peak, half-max area in beams
  artifacts: FITS image, light curve PNG, montage PNG
Store: sqlite:///$HOME/mwa/mlflow/mlflow.db, artifacts in ~/mwa/mlflow/artifacts.

    ~/mwa/mlflow-venv/bin/python ~/mwa/events/log_event_mlflow.py --sun 1419137296 --cal 1419161128 \
        --ch 127 --datedir 20241225 [--label peak4s] [--note "..."]
"""
import argparse
import glob
import os
import re

import numpy as np
from astropy.io import fits

HOME = os.path.expanduser("~")
STORE = f"sqlite:///{HOME}/mwa/mlflow/mlflow.db"
ARTIFACTS = f"{HOME}/mwa/mlflow/artifacts"
SCRATCH = f"/scratch/{os.environ.get('USER', 'andre_csillaghy')}"


def image_stats(fn):
    h = fits.getheader(fn)
    d = np.squeeze(fits.getdata(fn)).astype(float)
    while d.ndim > 2:          # first Stokes plane (I)
        d = d[0]
    s = 3600.0 if h.get("CUNIT1", "deg").strip().lower().startswith("deg") else 1.0
    x = ((np.arange(d.shape[1]) - (h["CRPIX1"] - 1)) * h["CDELT1"] + h["CRVAL1"]) * s
    y = ((np.arange(d.shape[0]) - (h["CRPIX2"] - 1)) * h["CDELT2"] + h["CRVAL2"]) * s
    X, Y = np.meshgrid(x, y)
    off = d[(np.hypot(X, Y) > 2500) & np.isfinite(d)]
    rms = 1.4826 * np.nanmedian(np.abs(off - np.nanmedian(off)))
    pk = np.nanmax(d)
    m = d > 0.5 * pk
    cx, cy = (d[m] * X[m]).sum() / d[m].sum(), (d[m] * Y[m]).sum() / d[m].sum()
    bmaj, bmin = h["BMAJ"] * 3600, h["BMIN"] * 3600
    omega_beam = np.pi / (4 * np.log(2)) * bmaj * bmin                    # arcsec^2
    nu = next((h[f"CRVAL{k}"] for k in range(1, 5) if str(h.get(f"CTYPE{k}", "")).startswith("FREQ")), np.nan)
    tb = pk * 1e-26 * (2.998e8 / nu) ** 2 / (2 * 1.380649e-23 * omega_beam / 206265 ** 2)
    return dict(peak_jy_beam=pk, rms_jy_beam=rms, peak_over_rms=pk / rms, x_arcsec=cx, y_arcsec=cy,
                r_rsun=np.hypot(cx, cy) / 960, bmaj_arcsec=bmaj, bmin_arcsec=bmin, tb_rj_k=tb,
                halfmax_beams=m.sum() * (abs(h["CDELT1"]) * s) ** 2 / omega_beam), nu, h.get("DATE-OBS", "")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sun", required=True)
    ap.add_argument("--cal", required=True)
    ap.add_argument("--ch", default="127")
    ap.add_argument("--datedir", required=True)
    ap.add_argument("--label", default="peak4s")
    ap.add_argument("--tres", default="4")
    ap.add_argument("--note", default="")
    a = ap.parse_args()

    import mlflow
    mlflow.set_tracking_uri(STORE)
    if mlflow.get_experiment_by_name("archive-bursts") is None:
        mlflow.create_experiment("archive-bursts", artifact_location=f"file://{ARTIFACTS}")
    mlflow.set_experiment("archive-bursts")

    tag = f"{a.sun}_ch{a.ch}"
    w = f"{SCRATCH}/mwa/events/{a.sun}"
    peak = open(f"{w}/peak.txt").read() if os.path.exists(f"{w}/peak.txt") else ""
    window = re.search(r"TRANGE=(\S+)", peak)
    imgdir = glob.glob(f"{SCRATCH}/paircars/out/{tag}/{a.datedir}/{a.sun}_target/imagedir_*_{a.label}")
    images = sorted(glob.glob(f"{imgdir[0]}/pbcor_hpcs/*.fits")) if imgdir else []
    version = open(f"{HOME}/mwa/events/VERSION").read().strip() if os.path.exists(f"{HOME}/mwa/events/VERSION") else ""
    lc = f"{HOME}/mwa/events/{tag}_lightcurve.png"
    montage = f"{SCRATCH}/overnight/analysis/{tag}_{a.label}.png"
    for fn in images:
        stats, nu, t = image_stats(fn)
        with mlflow.start_run(run_name=f"{a.sun} ch{a.ch} {t[11:19]}"):
            mlflow.log_params(dict(obsid=a.sun, calibrator=a.cal, coarse_channel=a.ch,
                                   freq_mhz=round(nu / 1e6, 3), window=window.group(1) if window else "",
                                   image_time=t, image_timeres_s=a.tres, label=a.label,
                                   pipeline="P-AIRCARS self-cal, pol I, no polcal", birli="no AOFlagger, 0.25 s, 160 kHz",
                                   window_rule="max 4 s mean of MWA short-baseline light curve, >= 8 s inside obs",
                                   sbm_commit=version))
            mlflow.log_metrics({k: float(v) for k, v in stats.items()})
            if a.note:
                mlflow.set_tag("note", a.note)
            mlflow.set_tag("fits_path", fn)
            for f in [fn, lc, montage]:
                if os.path.exists(f):
                    mlflow.log_artifact(f)
        print(f"logged {os.path.basename(fn)}: peak/rms {stats['peak_over_rms']:.0f}")
    if not images:
        print(f"no images for {tag} {a.label}")


if __name__ == "__main__":
    main()
