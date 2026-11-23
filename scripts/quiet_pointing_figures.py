#!/usr/bin/env python3
"""Haslam 1982 pointing figure for every quiet-noon catalogue scan.

Same layout as Oberoi 2017 Fig. 1 / figures/sharma2020/haslam_sky.png:
left the sky at 108 MHz, right the tile beam 90 / 9 / 0.9 %. Mid-scan
time. Does not invent maps.

    python scripts/quiet_pointing_figures.py
"""

from __future__ import annotations

import csv
import json
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("SUNPY_CONFIGDIR", tempfile.mkdtemp(prefix="sunpy-"))

import matplotlib

matplotlib.use("Agg")
import astropy.units as u
import matplotlib.pyplot as plt
import numpy as np
from astropy.coordinates import AltAz, EarthLocation, SkyCoord, get_body
from astropy.time import Time
from matplotlib.colors import LogNorm

from solarburst.haslam import HASLAM_ALPHA, HaslamMap
from solarburst.oberoi2017 import _altaz_grid, pointing_at, tile_power

CSV_PATH = ROOT / "configs/quiet/quiet_noon_2013_2015.csv"
OUTDIR = ROOT / "figures" / "quiet2015" / "pointing"
JSON_PATH = OUTDIR / "pointing.json"
FREQ_MHZ = 108.0
FIG4_OBSID = "1133149192"
FIG4_START = "2015-12-03T03:39:44"
FIG4_DURATION_S = 296


def mid_iso(start: str, duration_s: int) -> str:
    t0 = datetime.strptime(start, "%Y-%m-%dT%H:%M:%S")
    mid = t0 + timedelta(seconds=int(duration_s) / 2)
    return mid.strftime("%Y-%m-%dT%H:%M:%S")


def load_rows() -> list[dict]:
    rows = [
        {
            "obsid": FIG4_OBSID,
            "start": FIG4_START,
            "duration_s": FIG4_DURATION_S,
            "mid": mid_iso(FIG4_START, FIG4_DURATION_S),
        }
    ]
    with CSV_PATH.open() as f:
        for r in csv.DictReader(f):
            start = r["starttime_utc"].replace(".000Z", "").replace("Z", "")
            dur = int(float(r["duration"]))
            rows.append(
                {
                    "obsid": r["obs_id"],
                    "start": start,
                    "duration_s": dur,
                    "mid": mid_iso(start, dur),
                }
            )
    return rows


class Plotter:
    def __init__(self, *, step_deg: float = 1.0) -> None:
        self.step = step_deg
        self.hmap = HaslamMap()
        self.az_g, self.za_g, _ = _altaz_grid(step_deg)
        self.loc = EarthLocation.of_site("MWA")
        self.theta = np.deg2rad(self.az_g)

    def draw(self, out: Path, *, time: str, az0: float, za0: float, delays) -> None:
        t = Time(time)
        sky = SkyCoord(
            az=self.az_g * u.deg,
            alt=(90.0 - self.za_g) * u.deg,
            frame=AltAz(obstime=t, location=self.loc),
        )
        t_map = self.hmap.at_freq(sky, FREQ_MHZ * 1e6)
        p_n = tile_power(self.az_g, self.za_g, FREQ_MHZ * 1e6, delays)
        sun = get_body("sun", t, location=self.loc).transform_to(
            AltAz(obstime=t, location=self.loc)
        )
        vmin = max(30.0, float(np.nanpercentile(t_map, 5)))
        vmax = float(np.nanpercentile(t_map, 99.5))
        fig, axes = plt.subplots(
            1, 2, figsize=(11.2, 5.6), subplot_kw={"projection": "polar"},
            layout="constrained",
        )
        for ax in axes:
            ax.set_theta_zero_location("N")
            ax.set_theta_direction(-1)
            ax.set_thetagrids([0, 90, 180, 270], labels=["N", "E", "S", "W"])
            ax.set_rlim(0, 90)
            ax.set_yticks([30, 60, 90])
            ax.set_yticklabels(["30°", "60°", "90°"])
        mesh = axes[0].pcolormesh(
            self.theta, self.za_g, t_map, shading="nearest", cmap="inferno",
            norm=LogNorm(vmin=vmin, vmax=vmax),
        )
        fig.colorbar(mesh, ax=axes[0], pad=0.12, shrink=0.8).set_label(
            rf"$T$ at {FREQ_MHZ:.0f} MHz (K)"
        )
        axes[0].set_title("Haslam 1982, this pointing", fontsize=10)
        mesh2 = axes[1].pcolormesh(
            self.theta, self.za_g, t_map, shading="nearest", cmap="inferno",
            norm=LogNorm(vmin=vmin, vmax=vmax),
        )
        axes[1].contour(
            self.theta, self.za_g, p_n, levels=[0.009, 0.09, 0.9],
            colors="white", linewidths=0.8,
        )
        axes[1].plot(
            np.deg2rad(az0), za0, marker="+", color="cyan",
            markersize=10, markeredgewidth=1.5,
        )
        axes[1].plot(
            np.deg2rad(float(sun.az.deg)),
            90.0 - float(sun.alt.deg),
            marker="o", color="yellow", markersize=6, markeredgecolor="k",
        )
        fig.colorbar(mesh2, ax=axes[1], pad=0.12, shrink=0.8).set_label(
            rf"$T$ at {FREQ_MHZ:.0f} MHz (K)"
        )
        axes[1].set_title("same, with tile beam 90 / 9 / 0.9 %", fontsize=10)
        fig.suptitle(
            f"Haslam et al. 1982  ·  α={HASLAM_ALPHA}  ·  {time}  ·  "
            f"az={az0:.1f}° za={za0:.1f}°  ·  unfiltered LAMBDA map",
            fontsize=10,
        )
        out.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out, dpi=120)
        plt.close(fig)


def main() -> None:
    rows = load_rows()
    plotter = Plotter(step_deg=1.0)
    OUTDIR.mkdir(parents=True, exist_ok=True)
    recs = {}
    if JSON_PATH.exists():
        recs = json.loads(JSON_PATH.read_text())
    n = len(rows)
    for i, row in enumerate(rows, 1):
        obsid = row["obsid"]
        png = OUTDIR / f"{obsid}.png"
        if png.exists() and obsid in recs:
            print(f"{i}/{n} skip {obsid}", flush=True)
            continue
        punt = pointing_at(row["mid"])
        recs[obsid] = {
            "obsid": obsid,
            "start": row["start"],
            "mid": row["mid"],
            "az_deg": round(float(punt["az_deg"]), 2),
            "alt_deg": round(float(punt["alt_deg"]), 2),
            "za_deg": round(float(punt["za_deg"]), 2),
        }
        plotter.draw(
            png,
            time=row["mid"],
            az0=float(punt["az_deg"]),
            za0=float(punt["za_deg"]),
            delays=np.asarray(punt["delays"]),
        )
        JSON_PATH.write_text(json.dumps(recs, indent=2, sort_keys=True))
        print(f"{i}/{n} wrote {png.name} az={recs[obsid]['az_deg']} za={recs[obsid]['za_deg']}", flush=True)
    JSON_PATH.write_text(json.dumps(recs, indent=2, sort_keys=True))
    print(f"wrote {JSON_PATH} ({len(recs)} pointings)")


if __name__ == "__main__":
    main()
