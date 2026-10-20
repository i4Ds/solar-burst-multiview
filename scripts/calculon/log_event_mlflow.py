#!/usr/bin/env python3
"""Log one archive-burst image to MLflow (experiment "archive-bursts").

Reads what event_image.sh leaves behind: the window chosen from the MWA light curve
(peak.txt), the P-AIRCARS image(s) in pbcor_hpcs, the light-curve PNG and the
P-AIRCARS montage, and logs one run per image:
  name:      "<date> <time> <burst type>, <MHz> MHz"
  tags:      event_date, burst_type, phase, project, tier, status (+ any --tag k=v)
  params:    obsid, calibrator, channel, frequency, window, pipeline settings, git commit
  metrics:   peak (Jy/beam), off-Sun rms, peak/rms, half-max centroid (arcsec, R_sun),
             beam, Rayleigh-Jeans T_B of the peak, half-max area in beams
  artifacts: FITS image, image figure with Stonyhurst grid (event_figure.py),
             MWA light curve, P-AIRCARS montage, and any --artifact files
  description (Markdown): the key numbers and --note.
Logging the same image again updates its run (matched on obsid, label, image time).
Store: sqlite:///$HOME/mwa/mlflow/mlflow.db, artifacts in ~/mwa/mlflow/artifacts.

    ~/mwa/mlflow-venv/bin/python ~/mwa/events/log_event_mlflow.py --sun 1419137296 --cal 1419161128 \
        --ch 127 --datedir 20241225 --tag burst_type=II --tag phase=III --tag project=OA004 --tag tier=A \
        [--mark "x,y,label"] [--artifact context.png] [--status check] [--note "..."]
"""
import argparse
import glob
import os
import re
import subprocess
import tempfile

import numpy as np
from astropy.io import fits

HOME = os.path.expanduser("~")
STORE = f"sqlite:///{HOME}/mwa/mlflow/mlflow.db"
ARTIFACTS = f"{HOME}/mwa/mlflow/artifacts"
SCRATCH = f"/scratch/{os.environ.get('USER', 'andre_csillaghy')}"
EXPERIMENT_NOTE = """**One MWA image per solar radio burst** (plan item 7c; solar-burst-multiview
`docs/burst-imaging-plan.md`). Each run is one image: coarse channel 127 (162.5 MHz) unless
noted, 4 s at the maximum of the MWA short-baseline light curve, P-AIRCARS self-calibration,
Stokes I, no AOFlagger. Candidates come from e-Callisto (Australia-ASSA) bursts during
archived MWA Sun observations (i4Ds/STIX-MWA `_results/ecallisto_mwa_bursts`).

Columns worth showing: tags `event_date`, `burst_type`, `phase`, `status`; metrics
`peak_over_rms`, `peak_jy_beam`, `x_arcsec`, `y_arcsec`, `r_rsun`, `tb_rj_k`.
`status`: ok, check (something to verify, see the description), bad."""


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


def description(tags, stats, nu, t, window, note):
    lines = [f"**{tags.get('event_date', t[:10])} {tags.get('burst_type', '')}** — MWA {tags['obsid']}, "
             f"{nu / 1e6:.1f} MHz, 4 s from {t[11:21]} UTC (phase {tags.get('phase', '?')}, "
             f"project {tags.get('project', '?')}, tier {tags.get('tier', '?')})",
             "",
             f"- peak {stats['peak_jy_beam']:.3g} Jy/beam, off-Sun rms {stats['rms_jy_beam']:.3g}, "
             f"**peak/rms {stats['peak_over_rms']:.0f}**",
             f"- half-max centroid ({stats['x_arcsec']:.0f}″, {stats['y_arcsec']:.0f}″), "
             f"{stats['r_rsun']:.2f} R☉ projected; {stats['halfmax_beams']:.1f} beams above half max",
             f"- beam {stats['bmaj_arcsec']:.0f}″ × {stats['bmin_arcsec']:.0f}″; "
             f"T_B (Rayleigh–Jeans, beam) {stats['tb_rj_k']:.2g} K",
             f"- window {window} (max of the MWA light curve)",
             f"- status: **{tags.get('status', 'ok')}**"]
    if note:
        lines += ["", note]
    lines += ["", "Artifacts: `*_grid.png` image with Stonyhurst grid, `*_lightcurve.png` MWA light curve, "
              "FITS image, P-AIRCARS montage."]
    return "\n".join(lines)


def find_run(client, exp_id, obsid, label, t):
    q = f"params.obsid = '{obsid}' and params.label = '{label}' and params.image_time = '{t}'"
    runs = client.search_runs([exp_id], filter_string=q, max_results=1)
    return runs[0].info.run_id if runs else None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sun", required=True)
    ap.add_argument("--cal", required=True)
    ap.add_argument("--ch", default="127")
    ap.add_argument("--datedir", required=True)
    ap.add_argument("--label", default="peak4s")
    ap.add_argument("--tres", default="4")
    ap.add_argument("--tag", action="append", default=[], help="k=v, e.g. burst_type=II")
    ap.add_argument("--mark", action="append", default=[], help="passed to event_figure.py")
    ap.add_argument("--artifact", action="append", default=[], help="extra file to attach")
    ap.add_argument("--status", default="ok", choices=["ok", "check", "bad"])
    ap.add_argument("--note", default="")
    a = ap.parse_args()

    import mlflow
    from mlflow.tracking import MlflowClient
    mlflow.set_tracking_uri(STORE)
    exp = mlflow.get_experiment_by_name("archive-bursts")
    exp_id = exp.experiment_id if exp else mlflow.create_experiment("archive-bursts",
                                                                     artifact_location=f"file://{ARTIFACTS}")
    client = MlflowClient()
    client.set_experiment_tag(exp_id, "mlflow.note.content", EXPERIMENT_NOTE)
    mlflow.set_experiment("archive-bursts")

    tag = f"{a.sun}_ch{a.ch}"
    w = f"{SCRATCH}/mwa/events/{a.sun}"
    peak = open(f"{w}/peak.txt").read() if os.path.exists(f"{w}/peak.txt") else ""
    m = re.search(r"TRANGE=(\S+)", peak)
    window = m.group(1) if m else ""
    imgdir = glob.glob(f"{SCRATCH}/paircars/out/{tag}/{a.datedir}/{a.sun}_target/imagedir_*_{a.label}")
    images = sorted(glob.glob(f"{imgdir[0]}/pbcor_hpcs/*.fits")) if imgdir else []
    version = open(f"{HOME}/mwa/events/VERSION").read().strip() if os.path.exists(f"{HOME}/mwa/events/VERSION") else ""
    extra = [f"{HOME}/mwa/events/{tag}_lightcurve.png", f"{SCRATCH}/overnight/analysis/{tag}_{a.label}.png"] + a.artifact
    tags = dict(kv.split("=", 1) for kv in a.tag)
    tags.update(obsid=a.sun, status=a.status)
    for fn in images:
        stats, nu, t = image_stats(fn)
        tags.setdefault("event_date", t[:10])
        name = f"{t[:10]} {t[11:19]} {('type ' + tags['burst_type']) if 'burst_type' in tags else ''}, {nu / 1e6:.1f} MHz"
        run_id = find_run(client, exp_id, a.sun, a.label, t)
        with mlflow.start_run(run_id=run_id, run_name=None if run_id else name):
            if run_id:
                mlflow.set_tag("mlflow.runName", name)
            else:
                mlflow.log_params(dict(obsid=a.sun, calibrator=a.cal, coarse_channel=a.ch,
                                       freq_mhz=round(nu / 1e6, 3), window=window, image_time=t,
                                       image_timeres_s=a.tres, label=a.label,
                                       pipeline="P-AIRCARS self-cal, pol I, no polcal",
                                       birli="no AOFlagger, 0.25 s, 160 kHz",
                                       window_rule="max 4 s mean of MWA short-baseline light curve, >= 8 s inside obs",
                                       sbm_commit=version))
            mlflow.log_metrics({k: float(v) for k, v in stats.items()})
            mlflow.set_tags(tags)
            mlflow.set_tag("fits_path", fn)
            mlflow.set_tag("mlflow.note.content", description(tags, stats, nu, t, window, a.note))
            with tempfile.TemporaryDirectory() as tmp:
                grid = f"{tmp}/{tag}_{t[11:19].replace(':', '')}_grid.png"
                title = f"MWA {a.sun}, {nu / 1e6:.1f} MHz, Stokes I, {a.tres} s from {t[11:21]} UTC"
                cmd = [f"{HOME}/mwa/mlflow-venv/bin/python", f"{HOME}/mwa/events/event_figure.py", fn, grid,
                       "--title", title] + sum([["--mark", mk] for mk in a.mark], [])
                if subprocess.run(cmd, capture_output=True).returncode == 0:
                    mlflow.log_artifact(grid)
                for f in [fn] + extra:
                    if os.path.exists(f):
                        mlflow.log_artifact(f)
        print(f"{'updated' if run_id else 'logged'} {name}: peak/rms {stats['peak_over_rms']:.0f}")
    if not images:
        print(f"no images for {tag} {a.label}")


if __name__ == "__main__":
    main()
