#!/usr/bin/env python3
"""Overview of the archive campaign: one panel per imaged MWA event, its best image.

For every event in the product registry (~/mwa/products) the frame with the highest
peak/rms over all its single-channel runs is shown (composites are skipped), cropped to
+-1500 arcsec, each on its own colour scale, with the optical limb, a 15 deg Stonyhurst
grid and 50/90 % contours. Label: date and time, e-Callisto burst type, GOES class during
the observation, frequency, image length and peak/rms; "weak" below peak/rms 100.
Panels in date order. Events whose imaging failed (no Sun in the image) are left out with
--skip OBSID ... and listed at the bottom.

    ~/mwa/tools-venv/bin/python ~/mwa/events/archive_overview.py OUT.png [--skip 1387165944]
"""
import glob
import json
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import export_board as xb   # noqa: E402  registry helpers: legacy_state, image_dir, frame, grid_lines


def main():
    out = sys.argv[1]
    skip = sys.argv[sys.argv.index("--skip") + 1:] if "--skip" in sys.argv else []
    events = json.load(open(f"{xb.PR}/events.json"))
    best = {}   # sun -> (snr, fn, meta, crop, extent, product)
    for f in sorted(glob.glob(f"{xb.PR}/*.json")):
        if os.path.basename(f) == "events.json":
            continue
        p = json.load(open(f))
        if p.get("parts"):
            continue
        if p.get("legacy"):
            xb.legacy_state(p)
        d = xb.image_dir(p)
        for fn in sorted(glob.glob(f"{d}/*.fits")) if d else []:
            meta, crop, extent = xb.frame(fn)
            if meta["snr"] > best.get(p["sun"], (-1,))[0]:
                best[p["sun"]] = (meta["snr"], fn, meta, crop, extent, p)
    suns = sorted((s for s in best if s not in skip), key=lambda s: best[s][2]["t"])
    ncol = 5
    nrow = -(-len(suns) // ncol)
    fig, axs = plt.subplots(nrow, ncol, figsize=(3.2 * ncol, 3.9 * nrow + 0.6))
    for ax in axs.flat:
        ax.set_axis_off()
    for ax, sun in zip(axs.flat, suns):
        snr, fn, m, crop, ext, p = best[sun]
        e = events.get(sun, {})
        ax.imshow(crop, origin="lower", cmap="inferno", extent=ext, vmin=0, vmax=crop.max())
        X, Y = np.linspace(ext[0], ext[1], crop.shape[1]), np.linspace(ext[2], ext[3], crop.shape[0])
        ax.contour(X, Y, crop, levels=crop.max() * np.array([0.5, 0.9]), colors="cyan", linewidths=0.6)
        g = xb.grid_lines(m["t"])
        for ln in g["lines"]:
            seg = [q for q in ln["pts"]]
            xs = [q[0] if q else np.nan for q in seg]
            ys = [q[1] if q else np.nan for q in seg]
            ax.plot(xs, ys, color="white", lw=0.3, alpha=0.45)
        ax.add_patch(plt.Circle((0, 0), g["limb"], fill=False, color="cyan", lw=0.7))
        ax.set_xlim(-1450, 1450); ax.set_ylim(-1450, 1450)
        goes = ", ".join(x["cls"] for x in (e.get("goes") or [])) or "no GOES flare"
        typ = e.get("burst_type", "")
        typ = "" if typ in ("", "untyped") else f"type {typ}, "
        weak = snr < 100
        ax.set_title(f"{m['t'][:10]} {m['t'][11:19]}\n{typ}{goes}\n{m['freq_mhz']:.1f} MHz, {p['tres']} s, "
                     f"peak/rms {snr:.0f}{' (weak)' if weak else ''}", fontsize=8.5, color="0.45" if weak else "black")
    fig.suptitle(f"MWA archive campaign: {len(suns)} radio bursts imaged with P-AIRCARS self-calibration "
                 "(best image of each event, own colour scale; cyan: optical limb, 50/90 % contours; "
                 "white: 15° solar grid)", fontsize=10)
    if skip:
        fig.text(0.01, 0.005, "Not shown, imaging failed (no Sun in the image): " + ", ".join(
            f"{best[s][2]['t'][:10]} (MWA {s})" if s in best else s for s in skip), fontsize=8.5, color="0.35")
    fig.tight_layout(rect=(0, 0.015, 1, 0.97), h_pad=1.6)
    fig.savefig(out, dpi=110)
    for s in suns:
        snr, fn, m, crop, ext, p = best[s]
        print(s, p["product"], m["t"], m["freq_mhz"], round(snr), m["x"], m["y"], m["r_rsun"])


if __name__ == "__main__":
    main()
