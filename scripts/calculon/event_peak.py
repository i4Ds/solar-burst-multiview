#!/usr/bin/env python3
"""Pick the 4 s to image from the MWA dynamic spectrum of one coarse channel.

Input: npz from solarburst.dynspec (unix, freq_mhz, amp). The light curve is the
median over the fine channels of amp / its median over time, averaged over WIDTH s;
the window with the highest mean, at least EDGE s inside the observation, is the
image interval. Prints the P-AIRCARS --timerange and writes a PNG of the curve.

    python3 event_peak.py dynspec.npz OUT.png [--width 4] [--edge 8]
"""
import argparse
from datetime import datetime, timezone

import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("npz")
ap.add_argument("png")
ap.add_argument("--width", type=float, default=4.0)
ap.add_argument("--edge", type=float, default=8.0)
a = ap.parse_args()

d = np.load(a.npz)
t, amp = d["unix"], d["amp"]
with np.errstate(all="ignore"):
    lc = np.nanmedian(amp / np.nanmedian(amp, axis=1, keepdims=True), axis=0)
dt = np.median(np.diff(t))
n = max(1, int(round(a.width / dt)))
ok = np.isfinite(lc)
csum = np.concatenate([[0], np.cumsum(np.where(ok, lc, 0))])
cnt = np.concatenate([[0], np.cumsum(ok)])
mean = (csum[n:] - csum[:-n]) / np.maximum(cnt[n:] - cnt[:-n], 1)   # window starting at sample i
start = t[: len(mean)] - dt / 2
valid = (start >= t[0] + a.edge) & (start + a.width <= t[-1] - a.edge) & ((cnt[n:] - cnt[:-n]) >= 0.8 * n)
i = int(np.argmax(np.where(valid, mean, -np.inf)))
t0, t1 = start[i], start[i] + a.width


def fmt(x):
    return datetime.fromtimestamp(x, timezone.utc).strftime("%Y/%m/%d/%H:%M:%S")


print(f"TRANGE={fmt(t0)}~{fmt(t1)}")
print(f"PEAK={mean[i]:.2f} (median 1), freq {d['freq_mhz'].min():.2f}-{d['freq_mhz'].max():.2f} MHz")

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(9, 3), constrained_layout=True)
x = (t - t[0])
ax.plot(x, lc, lw=0.6, color="#3987e5", label="0.25 s")
ax.plot(start[: len(mean)] - t[0] + a.width / 2, mean, lw=1.2, color="#0d366b", label=f"{a.width:g} s mean")
ax.axvspan(t0 - t[0], t1 - t[0], color="#d6262b", alpha=0.3, label="image")
ax.set_xlabel(f"s after {fmt(t[0])} UTC")
ax.set_ylabel("amplitude / median")
ax.set_title(f"MWA short baselines, {d['freq_mhz'].min():.1f}-{d['freq_mhz'].max():.1f} MHz", loc="left", fontsize=9)
ax.legend(fontsize=8)
fig.savefig(a.png, dpi=100)
