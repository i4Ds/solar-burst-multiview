"""Checks of a Birli 0.25 s MS before imaging (docs/handover-raw-025s-session.md).

Runs inside the mwa-demo container (casacore, wsclean):
  singularity exec --bind /scratch --env OPENBLAS_NUM_THREADS=1 $MWA_DEMO_SIF \
    python3 raw-ms-check.py MS_025 MS_2S OUTDIR [FRAME_UTC]

1. time and frequency grid
2. flagged fraction per time step, burst window vs the rest
3. flagged fraction per fine channel
4. dirty images (wsclean, no calibration) of the same 2 s frame from both MSs:
   peak offset from the phase centre, peak/rms
5. short-baseline light curve, 0.25 s averaged to 2 s vs the 2 s MS
Results: OUTDIR/check.txt, OUTDIR/check.npz, OUTDIR/*-dirty.fits
"""
import subprocess
import sys
from pathlib import Path

import numpy as np
from astropy.io import fits
from astropy.time import Time
from casacore.tables import table

MAX_BL = 200.0  # m, short baselines for the light curve
BURST = ("2022-09-30T04:28:29", "2022-09-30T04:29:05")

ms25, ms2, outdir = sys.argv[1], sys.argv[2], Path(sys.argv[3])
frame = sys.argv[4] if len(sys.argv) > 4 else "2022-09-30T04:28:31"
outdir.mkdir(parents=True, exist_ok=True)
log = open(outdir / "check.txt", "w")


def say(*a):
    print(*a, flush=True)
    print(*a, file=log, flush=True)


def mjds(iso):
    return Time(iso, scale="utc").mjd * 86400.0


def isot(s):
    return Time(s / 86400.0, format="mjd").isot


def scan(ms, chunk_times=64):
    """Per time step: flagged fraction, short-baseline mean amplitude (XX+YY)/2,
    per channel flag counts. Rows are assumed time-ordered (Birli writes them so)."""
    t = table(ms, ack=False)
    pos = table(ms + "/ANTENNA", ack=False).getcol("POSITION")
    a1, a2 = t.getcol("ANTENNA1"), t.getcol("ANTENNA2")
    time = t.getcol("TIME")
    tt, start = np.unique(time, return_index=True)
    assert np.all(np.diff(start) > 0), "rows not time ordered"
    bl = np.linalg.norm(pos[a1] - pos[a2], axis=1)
    short_all = (a1 != a2) & (bl < MAX_BL)
    nchan = t.getcell("FLAG", 0).shape[0]
    ffrac = np.zeros(len(tt))
    amp = np.full(len(tt), np.nan)
    chflag, chtot = np.zeros(nchan), 0
    ends = np.r_[start[1:], t.nrows()]
    for i0 in range(0, len(tt), chunk_times):
        i1 = min(i0 + chunk_times, len(tt))
        r0, r1 = start[i0], ends[i1 - 1]
        fl = t.getcol("FLAG", r0, r1 - r0)
        d = t.getcol("DATA", r0, r1 - r0)
        cross = (a1[r0:r1] != a2[r0:r1])
        chflag += fl[cross].any(axis=2).sum(axis=0)
        chtot += cross.sum()
        a = 0.5 * (np.abs(d[..., 0]) + np.abs(d[..., 3]))
        good = ~(fl[..., 0] | fl[..., 3])
        for i in range(i0, i1):
            s, e = start[i] - r0, ends[i] - r0
            ffrac[i] = fl[s:e][cross[s:e]].mean()
            sel = short_all[r0 + s:r0 + e]
            g = good[s:e][sel]
            amp[i] = (a[s:e][sel] * g).sum() / max(g.sum(), 1)
    freq = table(ms + "/SPECTRAL_WINDOW", ack=False).getcol("CHAN_FREQ")[0]
    pairs = set(zip(a1[short_all][:20000], a2[short_all][:20000]))
    return dict(tt=tt, ffrac=ffrac, amp=amp, chflag=chflag / chtot, freq=freq,
                nshort=len(pairs))


def dirty(ms, i0, i1, name):
    """wsclean dirty image of time steps [i0, i1); returns peak offset (arcsec) and peak/rms."""
    stem = str(outdir / name)
    subprocess.run(["wsclean", "-name", stem, "-size", "512", "512", "-scale", "20asec",
                    "-weight", "briggs", "0", "-pol", "I", "-niter", "0", "-no-update-model-required",
                    "-interval", str(i0), str(i1), "-j", "16", ms],
                   check=True, stdout=subprocess.DEVNULL)
    h = fits.open(stem + "-dirty.fits")[0]
    im = h.data.squeeze()
    iy, ix = np.unravel_index(np.nanargmax(im), im.shape)
    dx = (ix - (h.header["CRPIX1"] - 1)) * h.header["CDELT1"] * 3600
    dy = (iy - (h.header["CRPIX2"] - 1)) * h.header["CDELT2"] * 3600
    ny, nx = im.shape
    edge = np.r_[im[:ny // 8].ravel(), im[-ny // 8:].ravel()]
    rms = np.sqrt(np.mean(edge ** 2))
    return dx, dy, im.max() / rms, (h.header["BMAJ"] * 3600, h.header["BMIN"] * 3600)


say(f"MS 0.25 s: {ms25}\nMS 2 s:    {ms2}")
r = scan(ms25)
q = scan(ms2)
np.savez(outdir / "check.npz", **{f"q25_{k}": v for k, v in r.items()},
         **{f"q2_{k}": v for k, v in q.items()})

# 1. grid
for lab, x in (("0.25 s", r), ("2 s", q)):
    dt = np.unique(np.round(np.diff(x["tt"]), 3))
    df = np.unique(np.round(np.diff(x["freq"]) / 1e3, 1))
    say(f"\n[1] {lab}: {len(x['tt'])} steps, dt {dt} s, {isot(x['tt'][0])} .. {isot(x['tt'][-1])}; "
        f"{len(x['freq'])} chan, df {df} kHz, {x['freq'][0]/1e6:.3f} .. {x['freq'][-1]/1e6:.3f} MHz")

# 2. flags in time
b = (r["tt"] >= mjds(BURST[0])) & (r["tt"] <= mjds(BURST[1]))
quack = r["ffrac"] > 0.99
say(f"\n[2] flagged fraction 0.25 s: overall {r['ffrac'].mean():.3f}; fully flagged steps {quack.sum()} "
    f"(first {np.argmin(quack) if quack[0] else 0} at the start)")
say(f"    burst {BURST[0][11:]}-{BURST[1][11:]}: mean {r['ffrac'][b].mean():.3f}, max {r['ffrac'][b].max():.3f}; "
    f"outside (excl. fully flagged): mean {r['ffrac'][~b & ~quack].mean():.3f}, "
    f"min {r['ffrac'][~b & ~quack].min():.3f}, max {r['ffrac'][~b & ~quack].max():.3f}")
say(f"    2 s MS: overall {q['ffrac'].mean():.3f}")

# 3. flags per channel
say("\n[3] flagged fraction per channel (cross-correlations, any pol)")
for f, c25 in zip(r["freq"], r["chflag"]):
    say(f"    {f/1e6:9.3f} MHz  {c25:.3f}")
say("    2 s MS: " + " ".join(f"{c:.3f}" for c in q["chflag"]))

# 5. light curve
say(f"\n[5] light curve, cross-correlations shorter than {MAX_BL:.0f} m "
    f"({r['nshort']} / {q['nshort']} baselines in 0.25 s / 2 s MS)")
avg = np.full(len(q["tt"]), np.nan)
for k, t2 in enumerate(q["tt"]):
    m = (np.abs(r["tt"] - t2) < 1.0) & ~quack
    if m.sum() == 8:
        avg[k] = r["amp"][m].mean()
ok = np.isfinite(avg) & np.isfinite(q["amp"]) & (q["amp"] > 0)
ratio = avg[ok] / q["amp"][ok]
cc = np.corrcoef(avg[ok], q["amp"][ok])[0, 1]
say(f"    {ok.sum()} common 2 s frames; ratio 0.25 s/2 s: median {np.median(ratio):.4f}, "
    f"16-84% {np.percentile(ratio, 16):.4f}..{np.percentile(ratio, 84):.4f}; correlation {cc:.4f}")
for k in np.argsort(q["amp"])[-5:][::-1]:
    say(f"    {isot(q['tt'][k])[11:22]}  2 s {q['amp'][k]:.4g}  0.25 s avg {avg[k]:.4g}")
ib = np.nanargmax(np.where(b, r["amp"], np.nan))
say(f"    0.25 s peak in the burst window: {isot(r['tt'][ib])[11:23]}, "
    f"{r['amp'][ib] / np.nanmedian(r['amp'][~quack]):.1f} x the median")

# 4. dirty images of the same 2 s frame
k = int(np.argmin(np.abs(q["tt"] - mjds(frame))))
idx = np.flatnonzero(np.abs(r["tt"] - q["tt"][k]) < 1.0)
say(f"\n[4] dirty images of the 2 s frame {isot(q['tt'][k])[11:22]} "
    f"(2 s step {k}, 0.25 s steps {idx[0]}..{idx[-1]}), no calibration")
for lab, ms, i0, i1 in (("2 s", ms2, k, k + 1), ("0.25 s x8", ms25, idx[0], idx[-1] + 1),
                        ("0.25 s x1", ms25, idx[3], idx[3] + 1)):
    name = "dirty_" + lab.replace(" ", "").replace(".", "p")
    dx, dy, snr, beam = dirty(ms, i0, i1, name)
    say(f"    {lab:10s} peak at ({dx:+6.0f}, {dy:+6.0f}) arcsec from the phase centre (RA, Dec), "
        f"peak/rms {snr:6.1f}, beam {beam[0]:.0f}x{beam[1]:.0f} arcsec")
say("\nRAW_MS_CHECK_DONE")
