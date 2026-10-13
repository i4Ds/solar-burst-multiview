"""Statistical significance of the sub-second peaks in the 0.25 s burst cube.

Input: the P-AIRCARS image cube of the 2022-09-30 04:28 type III burst at
148.5 MHz (coarse channel 116), 0.25 s frames, as written by make_cube.py:
data/flare20220930/overnight/1348547272_025s_ch116_c2_burst.npz
(data[t,1,y,x] in Jy/beam, primary-beam corrected; extent in arcsec).

What it measures, per frame:
  - off-Sun rms (r > 1400", MAD), i.e. the image noise, dynamic-range limited;
  - box sum and peak in a 600" box around the burst (+320", +110");
  - a single elliptical-Gaussian fit (centroid, widths).
Then:
  - noise on the box sum from the rms (correlated over one beam);
  - a conservative upper bound on per-frame noise: treat all frame-to-frame
    jitter as noise, sigma = 1.4826*MAD(second differences)/sqrt(6),
    computed over the main burst;
  - lag-1..4 autocorrelation of the residual after a 2 s running median;
  - peaks with prominence > 3 and > 5 sigma (upper bound), scipy.find_peaks.

Assumptions (not verified here): frames are 0.25 s apart (file times are
rounded to 0.1 s); the y axis of the cube increases upwards (matches the
movie scripts); P-AIRCARS self-calibration does not inject frame-to-frame
amplitude errors larger than the upper bound.

Usage: python scripts/burst025s_significance.py [cube.npz] [outdir]
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy.ndimage import median_filter
from scipy.optimize import curve_fit
from scipy.signal import find_peaks

CUBE = Path(sys.argv[1] if len(sys.argv) > 1 else
            "data/flare20220930/overnight/1348547272_025s_ch116_c2_burst.npz")
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else "figures/flare20220930")
T0 = 15.8          # seconds after 04:28:00 of the first frame
DT = 0.25
BOX_C, BOX_HALF = (320.0, 110.0), 300.0
MAIN = (14.5, 42.0)  # main burst, s after first frame (04:28:30.3-04:28:57.8)


def label(t):
    s = T0 + t
    return f"04:28:{s:05.2f}" if s < 60 else f"04:29:{s - 60:05.2f}"


def gauss2d(c, a, x0, y0, sx, sy, th, b):
    xx, yy = c
    ca, sa = np.cos(th) ** 2, np.sin(th) ** 2
    p = ca / (2 * sx**2) + sa / (2 * sy**2)
    q = -np.sin(2 * th) / (4 * sx**2) + np.sin(2 * th) / (4 * sy**2)
    r = sa / (2 * sx**2) + ca / (2 * sy**2)
    return a * np.exp(-(p * (xx - x0) ** 2 + 2 * q * (xx - x0) * (yy - y0) + r * (yy - y0) ** 2)) + b


def measure(cube):
    d = np.load(cube)
    data = d["data"][:, 0].astype(float)
    n = data.shape[1]
    ext = d["extent"]
    px = (ext[1] - ext[0]) / n
    x = ext[0] + px * (np.arange(n) + 0.5)
    X, Y = np.meshgrid(x, x)
    off = np.hypot(X, Y) > 1400
    box = (np.abs(X - BOX_C[0]) < BOX_HALF) & (np.abs(Y - BOX_C[1]) < BOX_HALF)
    bmaj, bmin, _ = d["beams"][0]
    beam_pix = 1.1331 * bmaj * bmin / px**2
    rows = []
    for k, f in enumerate(data):
        rms = 1.4826 * np.median(np.abs(f[off] - np.median(f[off])))
        z = f[box]
        i = z.argmax()
        p0 = [z.max(), X[box][i], Y[box][i], 60, 40, 0.3, 0]
        try:
            p, _ = curve_fit(gauss2d, (X[box], Y[box]), z, p0=p0, maxfev=20000)
        except RuntimeError:
            p = np.full(7, np.nan)
        rows.append(dict(t=k * DT, time=label(k * DT), rms=rms, peak=z.max(), boxsum=z.sum(),
                         boxsum_err=rms * np.sqrt(box.sum() * beam_pix),
                         x0=p[1], y0=p[2], area=abs(p[3] * p[4])))
    return rows, str(d["times"][0]), float(d["freqs"][0])


def stats(rows):
    t = np.array([r["t"] for r in rows])
    m = (t > MAIN[0]) & (t < MAIN[1])
    out = {}
    for key in ("boxsum", "peak"):
        y = np.array([r[key] for r in rows])
        d2 = (y[2:] - 2 * y[1:-1] + y[:-2])[m[1:-1]]
        sig = 1.4826 * np.median(np.abs(d2)) / np.sqrt(6)
        res = (y - median_filter(y, 9, mode="nearest"))[m]
        ac = [float(np.corrcoef(res[:-k], res[k:])[0, 1]) for k in (1, 2, 3, 4)]
        peaks = {}
        for ns in (3, 5):
            idx, pr = find_peaks(y, prominence=ns * sig)
            peaks[f"gt{ns}sigma"] = [dict(time=rows[i]["time"], t=float(t[i]), prominence_sigma=float(p / sig),
                                          x0=float(rows[i]["x0"]), y0=float(rows[i]["y0"]))
                                     for i, p in zip(idx, pr["prominences"])]
        out[key] = dict(sigma_upper=float(sig), sigma_upper_frac=float(sig / np.median(y[m])),
                        autocorr_lag1_4=ac, **peaks)
    rel = np.array([r["boxsum_err"] / r["boxsum"] for r in rows])
    x0 = np.array([r["x0"] for r in rows])[m]
    y0 = np.array([r["y0"] for r in rows])[m]
    out["boxsum_stat_err_frac_median"] = float(np.median(rel))
    out["main_centroid"] = dict(mean=[float(x0.mean()), float(y0.mean())], std=[float(x0.std()), float(y0.std())],
                                n=int(m.sum()))
    return out


def figure(rows, st, freq, png):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    ink, ink2, grid = "#0b0b0b", "#52514e", "#e4e3df"
    blue, orange = "#2a78d6", "#eb6834"
    t = np.array([r["t"] for r in rows]) + T0
    S = np.array([r["boxsum"] for r in rows]) / 1e6
    y0 = np.array([r["y0"] for r in rows])
    sig = st["boxsum"]["sigma_upper"] / 1e6
    pk = st["boxsum"]["gt5sigma"]
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(10, 6.2), sharex=True,
                                 gridspec_kw=dict(height_ratios=[2, 1], hspace=0.08))
    fig.patch.set_facecolor("#fcfcfb")
    for a in (a1, a2):
        a.set_facecolor("#fcfcfb")
        a.grid(True, color=grid, lw=0.6)
        for s in ("top", "right"):
            a.spines[s].set_visible(False)
        for s in ("left", "bottom"):
            a.spines[s].set_color(ink2)
        a.tick_params(colors=ink2, labelsize=9)
    a1.fill_between(t, S - sig, S + sig, color=blue, alpha=0.18, lw=0, label="±1σ upper bound (all jitter as noise)")
    a1.plot(t, S, color=blue, lw=2, marker="o", ms=3, label="box sum")
    for p in pk:
        i = int(round(p["t"] / DT))
        a1.plot(t[i], S[i], "v", color=orange, ms=8, mec="#fcfcfb", mew=1.5)
        if p["prominence_sigma"] >= 10:
            a1.annotate(f'{p["prominence_sigma"]:.0f}σ', (t[i], S[i]), xytext=(0, 8), textcoords="offset points",
                        ha="center", fontsize=8, color=ink2)
    a1.plot([], [], "v", color=orange, ms=8, label="peak, prominence > 5σ")
    a1.set_ylabel("box sum [10⁶ Jy/beam·pix]", color=ink, fontsize=10)
    a1.legend(frameon=False, fontsize=8.5, loc="upper right", labelcolor=ink2)
    a1.set_title(f"MWA {freq:.1f} MHz, 0.25 s frames, 2022-09-30: sub-second peaks of the 04:28 type III",
                 color=ink, fontsize=11, loc="left")
    mc = st["main_centroid"]
    a2.axhspan(mc["mean"][1] - mc["std"][1], mc["mean"][1] + mc["std"][1], color=ink2, alpha=0.12, lw=0)
    a2.plot(t, y0, color=blue, lw=0, marker="o", ms=3)
    for p in pk:
        i = int(round(p["t"] / DT))
        a2.plot(t[i], y0[i], "v", color=orange, ms=8, mec="#fcfcfb", mew=1.5)
    a2.set_ylim(50, 300)
    a2.set_ylabel("centroid Y [″]", color=ink, fontsize=10)
    a2.text(t[-1], mc["mean"][1] - mc["std"][1] - 16, "main burst mean ±1 std", ha="right", fontsize=8, color=ink2)
    ticks = np.arange(16, 72, 4)
    a2.set_xticks(ticks)
    a2.set_xticklabels([f"{s:02d}" if s < 60 else f"29:{s - 60:02d}" for s in ticks])
    a2.set_xlabel("seconds after 04:28:00 UTC", color=ink, fontsize=10)
    fig.savefig(png, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())


def main():
    rows, t_first, freq = measure(CUBE)
    st = stats(rows)
    OUT.mkdir(parents=True, exist_ok=True)
    stem = OUT / "burst025s_ch116_significance"
    json.dump(dict(cube=str(CUBE), first_frame=t_first, freq_mhz=freq, frame_s=DT, stats=st, frames=rows),
              open(f"{stem}.json", "w"), indent=1, default=float)
    figure(rows, st, freq, f"{stem}.png")
    b = st["boxsum"]
    print(f"stat. error of box sum: {st['boxsum_stat_err_frac_median']:.2%} (median)")
    print(f"upper-bound sigma: box sum {b['sigma_upper_frac']:.1%}, peak {st['peak']['sigma_upper_frac']:.1%} of median")
    print("residual autocorr lag 1-4:", np.round(b["autocorr_lag1_4"], 2))
    print(f"peaks > 5 sigma: {len(b['gt5sigma'])}; > 3 sigma: {len(b['gt3sigma'])}")
    for p in b["gt5sigma"]:
        print(f"  {p['time']}  {p['prominence_sigma']:5.1f} sigma  ({p['x0']:.0f}\", {p['y0']:.0f}\")")
    mc = st["main_centroid"]
    print(f"main-burst centroid ({mc['mean'][0]:.0f}\", {mc['mean'][1]:.0f}\") ± ({mc['std'][0]:.0f}, {mc['std'][1]:.0f}), n={mc['n']}")
    print(f"wrote {stem}.json and {stem}.png")


if __name__ == "__main__":
    main()
