#!/usr/bin/env python3
"""Reproduce Sharma & Oberoi 2020 Figure 4 as close as the FITS allow.

Two pieces, matching §4 of the paper:

1. Images — already on disk. CASA 5.3 ``clean``, SuperUniform, Hogbom,
   niter 8000, gain 0.1, 1024² × 50″, Stokes I, one 0.5 s frame. Read
   ``python scripts/sharma2020_fits_history.py``. Re-imaging with those
   numbers is ``scripts/calculon/sharma2020_casa_snap.py`` (no CASA here).

2. Kelvin — Oberoi 2017 whole-Sun flux, then Mohan & Oberoi 2017 F(ν) on
   **each** 0.5 s map (5σ radio Sun), then the time mean of T_B.

    python scripts/sharma2020_pipeline.py
    python scripts/sharma2020_pipeline.py --reuse

Does not use the 2022 factor 9.48. Does not overwrite fig4.png.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

from solarburst.config import REPO_ROOT, load, local_path
from solarburst.sharma2020 import BANDS, CLEAN, mean_tb_per_frame

_FIG4 = Path(__file__).with_name("sharma2020_fig4.py")
_spec = importlib.util.spec_from_file_location("sharma2020_fig4", _FIG4)
fig4 = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(fig4)


def load_s_odot(flux_dir: Path) -> dict[str, float]:
    out: dict[str, float] = {}
    for lab, _ch, _cap in BANDS:
        preferred = flux_dir / f"{lab}MHz_full.json"
        if not preferred.exists():
            raise SystemExit(f"missing {preferred} (Oberoi 2017 S_⊙)")
        rec = json.loads(preferred.read_text())
        out[lab] = float(rec["s_odot_sfu"])
        print(
            f"  {lab} MHz  S_⊙={out[lab]:.3f} SFU  r_N={rec.get('r_N')}  {preferred.name}",
            file=sys.stderr,
        )
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--config", default="sharma2022", help="where the FITS were staged")
    p.add_argument(
        "--flux-dir",
        type=Path,
        default=REPO_ROOT / "data" / "quiet2015" / "paper_flux",
    )
    p.add_argument("--reuse", action="store_true")
    p.add_argument("--nsig", type=float, default=5.0)
    p.add_argument(
        "--out",
        type=Path,
        default=REPO_ROOT / "figures" / "sharma2020" / "fig4_paper.png",
    )
    args = p.parse_args(argv)

    print("Imaging (from published FITS HISTORY, not re-run here):", file=sys.stderr)
    for k, v in CLEAN.items():
        print(f"  {k:14s} {v}", file=sys.stderr)
    print("Kelvin: per-frame Mohan F(ν) at 5σ, then time mean. No 9.48.", file=sys.stderr)

    cfg = load(args.config)
    fitsdir = local_path(cfg, cfg["remote"]["paths"]["fits"])
    fwd_dir = local_path(cfg, cfg["remote"]["paths"]["forward"])
    euv_dir = local_path(cfg, cfg["remote"]["paths"]["euv"])
    cache = REPO_ROOT / "data" / "quiet2015" / "fig4_tb_perframe.npz"
    args.out.parent.mkdir(parents=True, exist_ok=True)
    cache.parent.mkdir(parents=True, exist_ok=True)

    s_odot = load_s_odot(args.flux_dir)
    maps: dict[str, dict] = {}
    if args.reuse and cache.exists():
        packed = np.load(cache)
        for lab, ch, _ in BANDS:
            maps[lab] = {
                "tb": packed[f"{lab}_tb"],
                "extent": packed[f"{lab}_extent"],
                "bmaj_deg": float(packed[f"{lab}_bmaj_deg"]),
                "bmin_deg": float(packed[f"{lab}_bmin_deg"]),
                "bpa_deg": float(packed[f"{lab}_bpa_deg"]),
                "f_nu_mean": float(packed[f"{lab}_f_nu_mean"]),
                "f_nu_std": float(packed[f"{lab}_f_nu_std"]),
                "n": int(packed[f"{lab}_n"]),
            }
    else:
        for lab, ch, _ in BANDS:
            print(f"per-frame T_B {fig4.OBSID}-{ch}", file=sys.stderr)
            maps[lab] = mean_tb_per_frame(
                fitsdir, ch, s_odot[lab] * 1e4, nsig=args.nsig
            )
        payload = {}
        for lab, m in maps.items():
            payload[f"{lab}_tb"] = m["tb"]
            payload[f"{lab}_extent"] = m["extent"]
            payload[f"{lab}_bmaj_deg"] = m["bmaj_deg"]
            payload[f"{lab}_bmin_deg"] = m["bmin_deg"]
            payload[f"{lab}_bpa_deg"] = m["bpa_deg"]
            payload[f"{lab}_f_nu"] = m["f_nu"]
            payload[f"{lab}_f_nu_mean"] = m["f_nu_mean"]
            payload[f"{lab}_f_nu_std"] = m["f_nu_std"]
            payload[f"{lab}_n"] = m["n"]
        np.savez(cache, **payload)
        print(f"wrote {cache}", file=sys.stderr)

    print(f"{'MHz':>5s}  {'n':>4s}  {'F(ν)':>8s}  {'±':>6s}  {'peak MK':>8s}  {'caption':>8s}")
    for lab, ch, cap in BANDS:
        m = maps[lab]
        peak = float(np.nanmax(m["tb"])) / 1e6
        cap_s = f"{cap:8.2f}" if cap is not None else f"{'—':>8s}"
        print(
            f"{lab:>5s}  {m['n']:4d}  {m['f_nu_mean']:8.2f}  {m['f_nu_std']:6.2f}  "
            f"{peak:8.3f}  {cap_s}"
        )

    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(3, 3, figsize=(12.4, 12.0), layout="constrained")
    last_im = None
    for i, (lab, ch, _cap) in enumerate(BANDS[:3]):
        m = maps[lab]
        beam = (m["bmaj_deg"], m["bmin_deg"], m["bpa_deg"])
        last_im, _ = fig4._imshow_tb(
            axes[0, i], m["tb"], m["extent"], beam, f"MWA  {lab} MHz"
        )
    cell = float(cfg["imaging"]["cell_arcsec"])
    for i, (lab, sav_mhz, _paper) in enumerate(fig4.FWD_ROW):
        src = maps[{"109": "108", "162": "162", "217": "217"}[lab]]
        beam = (src["bmaj_deg"], src["bmin_deg"], src["bpa_deg"])
        sav = fwd_dir / f"20151203_{sav_mhz}MHz_psimas.sav"
        tb, extent = fig4.load_forward(sav, beam, cell)
        last_im, _ = fig4._imshow_tb(axes[1, i], tb, extent, beam, f"FORWARD  {lab} MHz")

    from solarburst.maps import aia_hpc_cutout

    aia_path = fig4._nearest_aia(euv_dir)
    aia, aia_ext = aia_hpc_cutout(aia_path, fov_arcsec=fig4.FOV_AIA)
    try:
        import sunpy.visualization.colormaps  # noqa: F401
        aia_cmap = "sdoaia193"
    except Exception:
        aia_cmap = "Oranges"
    for i, (lab, ch) in enumerate((("108", "084-085"), ("162", "125-126"), ("240", "187-188"))):
        m = maps[lab]
        tb_mk = m["tb"] / 1e6
        peak = float(np.nanmax(tb_mk))
        ax = axes[2, i]
        ax.imshow(aia, origin="lower", extent=aia_ext, cmap=aia_cmap, vmin=50, vmax=4000)
        ax.contour(
            tb_mk,
            levels=[f * peak for f in fig4.CONTOURS_AIA],
            extent=m["extent"],
            origin="lower",
            colors="cyan",
            linewidths=0.8,
        )
        beam = (m["bmaj_deg"], m["bmin_deg"], m["bpa_deg"])
        fig4._draw_disk(ax, beam, fov=fig4.FOV_AIA)
        ax.set_title(f"AIA 193 + {lab} MHz", fontsize=10)
    fig.colorbar(last_im, ax=axes[:2, :].ravel().tolist(), pad=0.02, shrink=0.9).set_label(
        r"$T_B$ (MK)"
    )
    fig.suptitle(
        "Sharma & Oberoi 2020 Fig. 4  ·  per-frame Mohan F(ν), then mean T_B",
        fontsize=11,
    )
    fig.savefig(args.out, dpi=160)
    plt.close(fig)
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
