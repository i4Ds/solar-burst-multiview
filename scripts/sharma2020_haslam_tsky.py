#!/usr/bin/env python3
"""Haslam 1982 T_Sky for the 2015-12-03 quiet scan, then recompute S_odot.

Uses the unfiltered Haslam et al. 1982 map (LAMBDA
``lambda_haslam408_nofilt.fits``), the same survey Oberoi 2017 cites.
Does not overwrite Rohit's tree or ``figures/sharma2020/fig4.png``.

    python scripts/sharma2020_haslam_tsky.py
    python scripts/sharma2020_haslam_tsky.py --check-2013
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

import numpy as np

from solarburst.config import REPO_ROOT
from solarburst.haslam import HASLAM_ALPHA, HASLAM_CITE, HASLAM_URL, HaslamMap, download_haslam
from solarburst.oberoi2017 import (
    OBEROI2013_AZ_DEG,
    OBEROI2013_TIME,
    OBEROI2013_ZA_DEG,
    QUIET2015_TIME,
    apply_sky_terms,
    pointing_at,
    sky_terms_haslam,
    table1_terms,
    tile_power,
    write_json,
)

BANDS = ("108", "162", "217", "240")


def _backup_table1(path: Path) -> Path | None:
    dest = path.with_name(path.stem + "_table1.json")
    if dest.exists():
        return dest
    shutil.copy2(path, dest)
    return dest


def plot_horizon(
    out: Path,
    *,
    freq_mhz: float,
    time: str,
    az0: float,
    za0: float,
    delays,
    step_deg: float = 1.0,
) -> None:
    """Alt-az view of Haslam + beam, same layout as Oberoi 2017 Fig. 1."""
    import astropy.units as u
    import matplotlib.pyplot as plt
    from astropy.coordinates import AltAz, EarthLocation, SkyCoord, get_body
    from astropy.time import Time
    from matplotlib.colors import LogNorm

    from solarburst.oberoi2017 import _altaz_grid

    loc = EarthLocation.of_site("MWA")
    t = Time(time)
    az_g, za_g, _ = _altaz_grid(step_deg)
    sky = SkyCoord(
        az=az_g * u.deg,
        alt=(90.0 - za_g) * u.deg,
        frame=AltAz(obstime=t, location=loc),
    )
    t_map = HaslamMap().at_freq(sky, freq_mhz * 1e6)
    p_n = tile_power(az_g, za_g, freq_mhz * 1e6, delays)
    sun = get_body("sun", t, location=loc).transform_to(AltAz(obstime=t, location=loc))

    theta = np.deg2rad(az_g)
    fig, axes = plt.subplots(
        1, 2, figsize=(11.2, 5.6), subplot_kw={"projection": "polar"}, layout="constrained"
    )
    for ax in axes:
        ax.set_theta_zero_location("N")
        ax.set_theta_direction(-1)
        ax.set_thetagrids([0, 90, 180, 270], labels=["N", "E", "S", "W"])
        ax.set_rlim(0, 90)
        ax.set_yticks([30, 60, 90])
        ax.set_yticklabels(["30°", "60°", "90°"])

    mesh = axes[0].pcolormesh(
        theta, za_g, t_map, shading="nearest", cmap="inferno",
        norm=LogNorm(vmin=max(30.0, np.nanpercentile(t_map, 5)), vmax=np.nanpercentile(t_map, 99.5)),
    )
    fig.colorbar(mesh, ax=axes[0], pad=0.12, shrink=0.8).set_label(rf"$T$ at {freq_mhz:.0f} MHz (K)")
    axes[0].set_title("Haslam 1982, this pointing", fontsize=10)

    mesh2 = axes[1].pcolormesh(
        theta, za_g, t_map, shading="nearest", cmap="inferno",
        norm=LogNorm(vmin=max(30.0, np.nanpercentile(t_map, 5)), vmax=np.nanpercentile(t_map, 99.5)),
    )
    axes[1].contour(
        theta, za_g, p_n, levels=[0.009, 0.09, 0.9], colors="white", linewidths=0.8
    )
    axes[1].plot(np.deg2rad(az0), za0, marker="+", color="cyan", markersize=10, markeredgewidth=1.5)
    axes[1].plot(
        np.deg2rad(float(sun.az.deg)),
        90.0 - float(sun.alt.deg),
        marker="o",
        color="yellow",
        markersize=6,
        markeredgecolor="k",
        label="Sun",
    )
    fig.colorbar(mesh2, ax=axes[1], pad=0.12, shrink=0.8).set_label(rf"$T$ at {freq_mhz:.0f} MHz (K)")
    axes[1].set_title("same, with tile beam 90 / 9 / 0.9 %", fontsize=10)
    fig.suptitle(
        f"Haslam et al. 1982  ·  α={HASLAM_ALPHA}  ·  {time}  ·  "
        f"az={az0:.1f}° za={za0:.1f}°  ·  unfiltered LAMBDA map",
        fontsize=10,
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=140)
    plt.close(fig)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--flux-dir", type=Path, default=REPO_ROOT / "data" / "quiet2015" / "paper_flux")
    p.add_argument("--tag", default="full", help="JSON suffix: full or 10s")
    p.add_argument("--check-2013", action="store_true")
    p.add_argument("--step", type=float, default=1.0, help="Haslam/beam grid, degrees")
    p.add_argument(
        "--out-fig",
        type=Path,
        default=REPO_ROOT / "figures" / "sharma2020" / "haslam_sky.png",
    )
    p.add_argument("--no-apply", action="store_true", help="compute T_Sky only, do not rewrite JSON")
    args = p.parse_args(argv)

    path = download_haslam()
    info = HaslamMap(path).info()
    print("Haslam 1982 map")
    print(f"  file   {path}")
    print(f"  url    {HASLAM_URL}")
    print(f"  cite   {HASLAM_CITE}")
    print(f"  nside  {info['nside']}  order={info['order']}  npix={info['npix']}")
    print(
        f"  T_408  {info['t408_K_min']:.1f}–{info['t408_K_max']:.1f} K  "
        f"median {info['t408_K_median']:.1f} K"
    )
    print(f"  sha256 {info['sha256']}")

    if args.check_2013:
        print(f"\n2013-09-03 check (Oberoi Fig. 1 pointing az=0 za={OBEROI2013_ZA_DEG})")
        print(f"{'MHz':>6s} {'T_Sky here':>10s} {'Table 1':>10s} {'Ω_P here':>10s} {'Table 1':>10s}")
        for freq in (103.0, 117.0, 167.0, 240.0):
            sky = sky_terms_haslam(
                freq,
                time=OBEROI2013_TIME,
                az_deg=OBEROI2013_AZ_DEG,
                za_deg=OBEROI2013_ZA_DEG,
                step_deg=args.step,
            )
            t1 = table1_terms(freq)
            print(
                f"{freq:6.0f} {sky['t_sky_K']:10.1f} {t1['t_sky_K']:10.1f} "
                f"{sky['omega_p_sr']:10.3f} {t1['omega_p_sr']:10.3f}"
            )

    punt = pointing_at(QUIET2015_TIME)
    print(
        f"\n2015-12-03 03:42 UT  Sun az={punt['az_deg']:.2f}°  "
        f"alt={punt['alt_deg']:.2f}°  za={punt['za_deg']:.2f}°"
    )
    print(f"delay steps {np.asarray(punt['delays']).tolist()}")

    sky_by_band: dict[str, dict] = {}
    print(f"\n{'band':>6s} {'T_Sky':>8s} {'T_b,Sky':>8s} {'2013 T_Sky':>10s} {'Ω_P beam':>8s} {'Ω_P T1':>8s}")
    for lab in BANDS:
        matches = sorted(args.flux_dir.glob(f"{lab}MHz_{args.tag}.json"))
        if not matches:
            print(f"{lab:>5s}  no {lab}MHz_{args.tag}.json", file=sys.stderr)
            continue
        rec = json.loads(matches[-1].read_text())
        sky = sky_terms_haslam(
            rec["freq_mhz"],
            time=QUIET2015_TIME,
            az_deg=float(punt["az_deg"]),
            za_deg=float(punt["za_deg"]),
            delays=np.asarray(punt["delays"]),
            step_deg=args.step,
        )
        sky_by_band[lab] = sky
        print(
            f"{lab:>5s} {sky['t_sky_K']:8.1f} {sky['t_b_sky_K']:8.2f} "
            f"{sky['t_sky_K_table1']:10.1f} {sky['omega_p_sr']:8.3f} "
            f"{sky['omega_p_sr_table1']:8.3f}"
        )

    if not args.no_apply:
        print(f"\n{'band':>6s} {'S_⊙ table1':>12s} {'S_⊙ Haslam':>12s} {'r_N':>8s}")
        for lab in BANDS:
            src = args.flux_dir / f"{lab}MHz_{args.tag}.json"
            if not src.exists() or lab not in sky_by_band:
                continue
            rec = json.loads(src.read_text())
            _backup_table1(src)
            out = apply_sky_terms(rec, sky_by_band[lab], use_table1_omega=True)
            write_json(out, src)
            print(
                f"{lab:>5s} {out.get('table1_s_odot_sfu'):12.3f} "
                f"{out.get('s_odot_sfu'):12.3f} {out.get('r_N'):8.3f}"
            )
            print(f"  wrote {src}")

    if sky_by_band:
        sky108 = sky_by_band.get("108") or next(iter(sky_by_band.values()))
        plot_horizon(
            args.out_fig,
            freq_mhz=float(sky108["freq_mhz"]),
            time=QUIET2015_TIME,
            az0=float(punt["az_deg"]),
            za0=float(punt["za_deg"]),
            delays=np.asarray(punt["delays"]),
            step_deg=args.step,
        )
        print(f"wrote {args.out_fig}")

        summary = {
            "haslam": info,
            "pointing": {
                "time": QUIET2015_TIME,
                "az_deg": punt["az_deg"],
                "alt_deg": punt["alt_deg"],
                "za_deg": punt["za_deg"],
                "delays": np.asarray(punt["delays"]).tolist(),
            },
            "bands": sky_by_band,
        }
        sum_path = args.flux_dir / "haslam_sky.json"
        write_json(summary, sum_path)
        print(f"wrote {sum_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
