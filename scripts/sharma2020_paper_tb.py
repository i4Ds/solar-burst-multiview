"""Sharma & Oberoi 2020 Fig. 4 with the paper flux scale (Oberoi + Mohan).

Time-mean of the staged CASA FITS (same images as fig4.png), then
F(ν) from Oberoi 2017 S_odot so the disk integral equals S_odot, then
T_B with Rayleigh–Jeans (Mohan & Oberoi 2017, scale=1). Writes
``figures/sharma2020/fig4_paper.png``; does not touch fig4.png.

    python scripts/sharma2020_paper_tb.py --flux-dir data/quiet2015/paper_flux
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import warnings
from pathlib import Path

import numpy as np
from astropy.io import fits
from astropy.wcs import FITSFixedWarning

from solarburst.config import REPO_ROOT, load, local_path
from solarburst.maps import (
    aia_hpc_cutout,
    frequency_hz,
    header_cell_arcsec,
    hpc_extent,
    load_casa_2d,
    solar_pixel,
)
from solarburst.mohan2017 import scale_image

warnings.filterwarnings("ignore", category=FITSFixedWarning)

_FIG4 = Path(__file__).with_name("sharma2020_fig4.py")
_spec = importlib.util.spec_from_file_location("sharma2020_fig4", _FIG4)
fig4 = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(fig4)

LABELS = ("108", "162", "217", "240")


def mean_jy_map(fitsdir: Path, channels: str, npix: int = 100) -> dict:
    paths = fig4._list_fits(fitsdir, channels)
    data0, hdr0 = load_casa_2d(paths[0])
    sun_xy = solar_pixel(hdr0)
    x0 = int(round(sun_xy[0] - (npix - 1) / 2.0))
    y0 = int(round(sun_xy[1] - (npix - 1) / 2.0))
    extent = hpc_extent(
        npix, npix, cell_arcsec=header_cell_arcsec(hdr0), sun_xy=sun_xy, origin=(x0, y0)
    )
    acc = np.zeros((npix, npix), dtype=np.float64)
    beams = []
    for i, path in enumerate(paths):
        data, hdr = load_casa_2d(path)
        acc += data[y0 : y0 + npix, x0 : x0 + npix]
        beams.append((float(hdr["BMAJ"]), float(hdr["BMIN"]), float(hdr.get("BPA", 0.0))))
        if (i + 1) % 150 == 0 or i + 1 == len(paths):
            print(f"  {channels}  {i + 1}/{len(paths)}", file=sys.stderr)
    mean = acc / len(paths)
    bmaj, bmin, bpa = np.median(np.asarray(beams), axis=0)
    hdr = hdr0.copy()
    hdr["BMAJ"] = float(bmaj)
    hdr["BMIN"] = float(bmin)
    # Crop is centred on the Sun; Mohan off-Sun RMS is measured from CRPIX.
    hdr["CRPIX1"] = (npix + 1) / 2.0
    hdr["CRPIX2"] = (npix + 1) / 2.0
    return {
        "jy": mean.astype(np.float32),
        "header": hdr,
        "extent": np.asarray(extent, dtype=np.float64),
        "bmaj_deg": float(bmaj),
        "bmin_deg": float(bmin),
        "bpa_deg": float(bpa),
        "n": len(paths),
        "freq_hz": frequency_hz(hdr0),
    }


def load_s_odot(flux_dir: Path) -> dict[str, float]:
    out: dict[str, float] = {}
    for lab in LABELS:
        preferred = flux_dir / f"{lab}MHz_full.json"
        matches = [preferred] if preferred.exists() else sorted(
            p for p in flux_dir.glob(f"{lab}MHz_*.json") if "table1" not in p.name
        )
        if not matches:
            raise SystemExit(f"no {lab}MHz_*.json in {flux_dir}")
        rec = json.loads(matches[-1].read_text())
        out[lab] = float(rec["s_odot_sfu"])
        print(
            f"  {lab} MHz  S_odot={out[lab]:.3f} SFU  r_N={rec.get('r_N')}  "
            f"from {matches[-1].name}",
            file=sys.stderr,
        )
    return out


def _header_from_npz(packed: np.lib.npyio.NpzFile, ch: str) -> fits.Header:
    h = fits.Header()
    ny, nx = packed[f"{ch}_jy"].shape
    h["CRPIX1"] = (nx + 1) / 2.0
    h["CRPIX2"] = (ny + 1) / 2.0
    h["CDELT1"] = float(packed[f"{ch}_cdelt1"])
    h["CDELT2"] = float(packed[f"{ch}_cdelt2"])
    h["BMAJ"] = float(packed[f"{ch}_bmaj_deg"])
    h["BMIN"] = float(packed[f"{ch}_bmin_deg"])
    return h


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--config", default="sharma2022")
    p.add_argument("--flux-dir", type=Path, required=True)
    p.add_argument("--reuse", action="store_true")
    p.add_argument("--nsig", type=float, default=5.0, help="Sharma 2020 uses 5σ")
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args(argv)

    cfg = load(args.config)
    fitsdir = fig4._fits_dir(cfg)
    fwd_dir = local_path(cfg, cfg["remote"]["paths"]["forward"])
    euv_dir = local_path(cfg, cfg["remote"]["paths"]["euv"])
    cache = REPO_ROOT / "data" / "quiet2015" / "fig4_paper_jy.npz"
    out = args.out or (REPO_ROOT / "figures" / "sharma2020" / "fig4_paper.png")
    out.parent.mkdir(parents=True, exist_ok=True)
    cache.parent.mkdir(parents=True, exist_ok=True)

    s_odot = load_s_odot(args.flux_dir)
    needed = {ch for _, ch, _ in fig4.MWA_TOP} | {ch for _, ch in fig4.MWA_BOTTOM}
    maps: dict[str, dict] = {}
    if args.reuse and cache.exists():
        packed = np.load(cache)
        for ch in needed:
            maps[ch] = {
                "jy": packed[f"{ch}_jy"],
                "extent": packed[f"{ch}_extent"],
                "bmaj_deg": float(packed[f"{ch}_bmaj_deg"]),
                "bmin_deg": float(packed[f"{ch}_bmin_deg"]),
                "bpa_deg": float(packed[f"{ch}_bpa_deg"]),
                "freq_hz": float(packed[f"{ch}_freq_hz"]),
                "header": _header_from_npz(packed, ch),
            }
    else:
        for ch in sorted(needed):
            print(f"averaging Jy {fig4.OBSID}-{ch}", file=sys.stderr)
            maps[ch] = mean_jy_map(fitsdir, ch)
        payload = {}
        for ch, m in maps.items():
            payload[f"{ch}_jy"] = m["jy"]
            payload[f"{ch}_extent"] = m["extent"]
            payload[f"{ch}_bmaj_deg"] = m["bmaj_deg"]
            payload[f"{ch}_bmin_deg"] = m["bmin_deg"]
            payload[f"{ch}_bpa_deg"] = m["bpa_deg"]
            payload[f"{ch}_freq_hz"] = m["freq_hz"]
            payload[f"{ch}_crpix1"] = float(m["header"]["CRPIX1"])
            payload[f"{ch}_crpix2"] = float(m["header"]["CRPIX2"])
            payload[f"{ch}_cdelt1"] = float(m["header"]["CDELT1"])
            payload[f"{ch}_cdelt2"] = float(m["header"]["CDELT2"])
        np.savez(cache, **payload)
        print(f"wrote {cache}", file=sys.stderr)

    scaled = {}
    print(f"{'band':5s} {'S_odot SFU':>10s} {'S\' Jy':>10s} {'F(ν)':>10s} {'peak MK':>8s} {'paper':>6s}")
    caption = {"108": 0.92, "162": 1.20, "217": 1.50, "240": float("nan")}
    for lab, ch, _ in list(fig4.MWA_TOP) + [("240", "187-188", None)]:
        if lab in scaled:
            continue
        m = maps[ch]
        rec = scale_image(
            np.asarray(m["jy"]),
            m["header"],
            s_odot[lab] * 1e4,
            nsig=args.nsig,
            freq_hz=float(m["freq_hz"]),
        )
        rec["extent"] = m["extent"]
        rec["beam"] = (m["bmaj_deg"], m["bmin_deg"], m["bpa_deg"])
        scaled[lab] = rec
        peak = rec["tb_K"].max() / 1e6
        print(
            f"{lab:5s} {s_odot[lab]:10.3f} {rec['s_prime_jy']:10.3e} "
            f"{rec['f_nu']:10.4g} {peak:8.3f} {caption[lab]:6.2f}"
        )

    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(3, 3, figsize=(12.4, 12.0), layout="constrained")
    last_im = None
    for i, (lab, ch, _paper) in enumerate(fig4.MWA_TOP):
        rec = scaled[lab]
        last_im, _ = fig4._imshow_tb(
            axes[0, i], rec["tb_K"], rec["extent"], rec["beam"], f"MWA  {lab} MHz  (paper scale)"
        )
    cell = float(cfg["imaging"]["cell_arcsec"])
    for i, (lab, sav_mhz, _paper) in enumerate(fig4.FWD_ROW):
        rec = scaled[{"109": "108", "162": "162", "217": "217"}[lab]]
        sav = fwd_dir / f"20151203_{sav_mhz}MHz_psimas.sav"
        tb, extent = fig4.load_forward(sav, rec["beam"], cell)
        last_im, _ = fig4._imshow_tb(axes[1, i], tb, extent, rec["beam"], f"FORWARD  {lab} MHz")

    aia_path = fig4._nearest_aia(euv_dir)
    aia, aia_ext = aia_hpc_cutout(aia_path, fov_arcsec=fig4.FOV_AIA)
    try:
        import sunpy.visualization.colormaps  # noqa: F401
        aia_cmap = "sdoaia193"
    except Exception:
        aia_cmap = "Oranges"
    for i, (lab, ch) in enumerate(fig4.MWA_BOTTOM):
        rec = scaled[lab]
        tb_mk = rec["tb_K"] / 1e6
        peak = float(np.nanmax(tb_mk))
        ax = axes[2, i]
        ax.imshow(aia, origin="lower", extent=aia_ext, cmap=aia_cmap, vmin=50, vmax=4000)
        ax.contour(
            tb_mk,
            levels=[f * peak for f in fig4.CONTOURS_AIA],
            extent=rec["extent"],
            origin="lower",
            colors="cyan",
            linewidths=0.8,
        )
        fig4._draw_disk(ax, rec["beam"], fov=fig4.FOV_AIA)
        ax.set_title(f"AIA 193 + {lab} MHz", fontsize=10)
    fig.colorbar(last_im, ax=axes[:2, :].ravel().tolist(), pad=0.02, shrink=0.9).set_label(
        r"$T_B$ (MK)"
    )
    fig.suptitle(
        "Sharma & Oberoi 2020 Fig. 4  ·  Oberoi 2017 S_⊙ + Mohan 2017 F(ν)  ·  not fig4.png",
        fontsize=11,
    )
    fig.savefig(out, dpi=160)
    plt.close(fig)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
