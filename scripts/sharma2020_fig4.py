"""Rebuild Sharma & Oberoi (2020, ApJ 903, 126) Figure 4 from staged products.

Top: time-mean MWA T_B at 108, 162 and 217 MHz (obsid 1133149192,
03:39:36–03:44:32 UT). Middle: FORWARD Stokes I at 108, 160 and 217 MHz,
convolved with the matching MWA restoring beam. Bottom: AIA 193 Å with
MWA contours at 108, 162 and 240 MHz.

    python scripts/sharma2020_fig4.py
    python scripts/sharma2020_fig4.py --reuse   # skip re-averaging FITS

Paper caption peaks: MWA 0.92, 1.20, 1.50 MK; FORWARD 1.59, 1.60, 1.61 MK.

``imaging.tb_scale`` (9.48) is a 2022 pickle/FITS ratio, not the 2020
method. It makes these maps match Sharma et al. 2022 stored cubes. For
Figure 4 as Sharma & Oberoi 2020 made it (Oberoi 2017 flux + Mohan 2017
F(ν), no 9.48) run ``scripts/sharma2020_fig4_exact.py``.
"""

from __future__ import annotations

import argparse
import sys
import warnings
from pathlib import Path

import numpy as np
from astropy.convolution import Gaussian2DKernel, convolve
from astropy.wcs import FITSFixedWarning
from matplotlib.patches import Circle, Ellipse
from scipy.io import readsav

from solarburst.config import REPO_ROOT, load, local_path
from solarburst.maps import (
    aia_hpc_cutout,
    frequency_hz,
    hpc_extent,
    header_cell_arcsec,
    jybeam_to_tb,
    load_casa_2d,
    solar_pixel,
)

warnings.filterwarnings("ignore", category=FITSFixedWarning)

RSUN = 958.0
OBSID = "1133149192"
# Paper labels vs MWA coarse-channel pairs in the working tree.
MWA_TOP = (
    ("108", "084-085", 0.92),
    ("162", "125-126", 1.20),
    ("217", "169-170", 1.50),
)
MWA_BOTTOM = (
    ("108", "084-085"),
    ("162", "125-126"),
    ("240", "187-188"),
)
FWD_ROW = (
    ("109", "108", 1.59),
    ("162", "160", 1.60),
    ("217", "217", 1.61),
)
CONTOURS_TB = (0.70, 0.75, 0.80, 0.85, 0.90, 0.95)
CONTOURS_AIA = (0.25, 0.35, 0.45, 0.55, 0.65, 0.75, 0.85, 0.95)
CUT_MK = 0.2
FOV = 2500.0
FOV_AIA = 1400.0
VMAX = 1.7


def _fits_dir(cfg: dict) -> Path:
    return local_path(cfg, cfg["remote"]["paths"]["fits"])


def _list_fits(fitsdir: Path, channels: str) -> list[Path]:
    stem = f"{OBSID}-{channels}"
    paths = sorted(fitsdir.glob(f"{stem}.*.image_image.FITS"))
    if not paths:
        paths = sorted(fitsdir.glob(f"{stem}.*.image.FITS"))
    if not paths:
        raise FileNotFoundError(f"no FITS for {stem} in {fitsdir}")
    return paths


def mean_tb_map(fitsdir: Path, channels: str, scale: float, npix: int = 100) -> dict:
    """Time-mean T_B. Sun pixel from the first frame; 4 min of motion is ≪ 1 pixel."""
    paths = _list_fits(fitsdir, channels)
    data0, hdr0 = load_casa_2d(paths[0])
    sun_xy = solar_pixel(hdr0)
    x0 = int(round(sun_xy[0] - (npix - 1) / 2.0))
    y0 = int(round(sun_xy[1] - (npix - 1) / 2.0))
    origin = (x0, y0)
    extent = hpc_extent(
        npix, npix, cell_arcsec=header_cell_arcsec(hdr0), sun_xy=sun_xy, origin=origin
    )
    acc = np.zeros((npix, npix), dtype=np.float64)
    beams = []
    for i, path in enumerate(paths):
        data, hdr = load_casa_2d(path)
        tb = jybeam_to_tb(
            data,
            frequency_hz(hdr),
            float(hdr["BMAJ"]),
            float(hdr["BMIN"]),
            scale=scale,
        )
        acc += tb[y0 : y0 + npix, x0 : x0 + npix]
        beams.append((float(hdr["BMAJ"]), float(hdr["BMIN"]), float(hdr.get("BPA", 0.0))))
        if (i + 1) % 150 == 0 or i + 1 == len(paths):
            print(f"  {channels}  {i + 1}/{len(paths)}", file=sys.stderr)
    mean = acc / len(paths)
    bmaj, bmin, bpa = np.median(np.asarray(beams), axis=0)
    return {
        "tb": mean.astype(np.float32),
        "extent": np.asarray(extent, dtype=np.float64),
        "bmaj_deg": float(bmaj),
        "bmin_deg": float(bmin),
        "bpa_deg": float(bpa),
        "n": len(paths),
    }


def load_forward(path: Path, beam: tuple[float, float, float], cell_arcsec: float) -> tuple[np.ndarray, list[float]]:
    sav = readsav(str(path), python_dict=True)
    rec = sav["quantmap"][0]
    tb = np.asarray(rec["DATA"], dtype=np.float64)
    dx = float(rec["DX"])  # R_sun
    rsun_arcsec = float(RSUN)
    cell = dx * rsun_arcsec
    ny, nx = tb.shape
    half_x = nx / 2.0 * cell
    half_y = ny / 2.0 * cell
    extent = [-half_x, half_x, -half_y, half_y]
    bmaj, bmin, bpa = beam
    fwhm_to_sigma = 1.0 / 2.35482004503
    kernel = Gaussian2DKernel(
        x_stddev=(bmin * 3600.0) * fwhm_to_sigma / cell_arcsec,
        y_stddev=(bmaj * 3600.0) * fwhm_to_sigma / cell_arcsec,
        theta=np.radians(bpa),
    )
    conv = convolve(tb, kernel, normalize_kernel=True, nan_treatment="fill")
    return conv, extent


def _nearest_aia(euv_dir: Path, stamp: str = "2015-12-03T03_41") -> Path:
    cands = sorted(euv_dir.glob(f"aia.lev1.193A_{stamp}*.fits"))
    if not cands:
        cands = sorted(euv_dir.glob("aia.lev1.193A_2015-12-03T03_4*.fits"))
    if not cands:
        raise FileNotFoundError(f"no AIA 193 near {stamp} in {euv_dir}")
    return cands[len(cands) // 2]


def _draw_disk(ax, beam: tuple[float, float, float] | None, fov: float = FOV) -> None:
    for r in (1.0, 2.0):
        ax.add_patch(Circle((0.0, 0.0), r * RSUN, fill=False, color="saddlebrown", lw=1.4))
    if beam is not None:
        bmaj, bmin, bpa = beam
        bx = -0.80 * fov
        by = -0.80 * fov
        ax.add_patch(
            Ellipse(
                (bx, by),
                width=bmin * 3600.0,
                height=bmaj * 3600.0,
                angle=-bpa,
                fill=False,
                color="black",
                lw=1.1,
            )
        )
    ax.set_xlim(-fov, fov)
    ax.set_ylim(-fov, fov)
    ax.set_aspect("equal")
    ax.grid(ls=":", color="0.7", lw=0.5)
    ax.set_xlabel("Solar X (arcsec)")
    ax.set_ylabel("Solar Y (arcsec)")
    ax.tick_params(direction="in", length=3)


def _imshow_tb(ax, tb, extent, beam, title, contours=CONTOURS_TB, cmap="jet"):
    tb_mk = tb / 1e6
    peak = float(np.nanmax(tb_mk))
    shown = np.where(tb_mk > CUT_MK, tb_mk, np.nan)
    im = ax.imshow(
        shown,
        origin="lower",
        extent=extent,
        cmap=cmap,
        vmin=0.0,
        vmax=VMAX,
        interpolation="nearest",
    )
    if peak > 0:
        ax.contour(
            tb_mk,
            levels=[f * peak for f in contours],
            extent=extent,
            origin="lower",
            colors="black",
            linewidths=0.7,
        )
    _draw_disk(ax, beam, fov=FOV)
    ax.set_title(title, fontsize=10)
    ax.text(0.03, 0.97, f"peak {peak:.2f} MK", transform=ax.transAxes, va="top", fontsize=8)
    return im, peak


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--config", default="sharma2022")
    p.add_argument("--reuse", action="store_true", help="reuse cached mean maps")
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args(argv)

    cfg = load(args.config)
    scale = float(cfg["imaging"].get("tb_scale", 9.48))
    print(
        f"tb_scale={scale:g} matches 2022 pickles, not Sharma & Oberoi 2020. "
        "Paper method: python scripts/sharma2020_fig4_exact.py",
        file=sys.stderr,
    )
    cell = float(cfg["imaging"]["cell_arcsec"])
    fitsdir = _fits_dir(cfg)
    fwd_dir = local_path(cfg, cfg["remote"]["paths"]["forward"])
    euv_dir = local_path(cfg, cfg["remote"]["paths"]["euv"])
    cache = REPO_ROOT / "data" / "quiet2015" / "fig4_means.npz"
    out = args.out or (REPO_ROOT / "figures" / "sharma2020" / "fig4.png")
    out.parent.mkdir(parents=True, exist_ok=True)
    cache.parent.mkdir(parents=True, exist_ok=True)

    needed = {ch for _, ch, _ in MWA_TOP} | {ch for _, ch in MWA_BOTTOM}
    maps: dict[str, dict] = {}
    if args.reuse and cache.exists():
        packed = np.load(cache, allow_pickle=False)
        for ch in needed:
            maps[ch] = {
                "tb": packed[f"{ch}_tb"],
                "extent": packed[f"{ch}_extent"].tolist(),
                "bmaj_deg": float(packed[f"{ch}_bmaj"]),
                "bmin_deg": float(packed[f"{ch}_bmin"]),
                "bpa_deg": float(packed[f"{ch}_bpa"]),
                "n": int(packed[f"{ch}_n"]),
            }
        print(f"reused {cache}", file=sys.stderr)
    else:
        for ch in sorted(needed):
            print(f"averaging {OBSID} {ch}  tb_scale={scale}", file=sys.stderr)
            maps[ch] = mean_tb_map(fitsdir, ch, scale)
        payload = {}
        for ch, m in maps.items():
            payload[f"{ch}_tb"] = m["tb"]
            payload[f"{ch}_extent"] = np.asarray(m["extent"])
            payload[f"{ch}_bmaj"] = m["bmaj_deg"]
            payload[f"{ch}_bmin"] = m["bmin_deg"]
            payload[f"{ch}_bpa"] = m["bpa_deg"]
            payload[f"{ch}_n"] = m["n"]
        np.savez_compressed(cache, **payload)
        print(f"wrote {cache}", file=sys.stderr)

    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(3, 3, figsize=(12.4, 12.0), layout="constrained")
    last_im = None
    print(f"{'panel':8s} {'peak MK':>8s} {'paper':>6s} {'ratio':>6s}  n")
    for i, (label, ch, paper) in enumerate(MWA_TOP):
        m = maps[ch]
        beam = (m["bmaj_deg"], m["bmin_deg"], m["bpa_deg"])
        last_im, peak = _imshow_tb(
            axes[0, i], m["tb"], m["extent"], beam, f"MWA  {label} MHz"
        )
        ratio = peak / paper
        print(f"MWA {label:5s} {peak:8.3f} {paper:6.2f} {ratio:6.3f}  {m['n']}")

    for i, (label, sav_mhz, paper) in enumerate(FWD_ROW):
        ch = MWA_TOP[i][1]
        m = maps[ch]
        beam = (m["bmaj_deg"], m["bmin_deg"], m["bpa_deg"])
        sav = fwd_dir / f"20151203_{sav_mhz}MHz_psimas.sav"
        tb, extent = load_forward(sav, beam, cell)
        last_im, peak = _imshow_tb(
            axes[1, i], tb, extent, beam, f"FORWARD  {label} MHz"
        )
        ratio = peak / paper
        print(f"FWD {label:5s} {peak:8.3f} {paper:6.2f} {ratio:6.3f}")

    aia_path = _nearest_aia(euv_dir)
    aia, aia_ext = aia_hpc_cutout(aia_path, fov_arcsec=FOV_AIA)
    print(f"AIA {aia_path.name}", file=sys.stderr)
    try:
        import sunpy.visualization.colormaps  # noqa: F401  registers sdoaia193
        aia_cmap = "sdoaia193"
    except Exception:
        aia_cmap = "Oranges"

    for i, (label, ch) in enumerate(MWA_BOTTOM):
        ax = axes[2, i]
        m = maps[ch]
        tb_mk = m["tb"] / 1e6
        peak = float(np.nanmax(tb_mk))
        ax.imshow(aia, origin="lower", extent=aia_ext, cmap=aia_cmap, vmin=50, vmax=4000)
        ax.contour(
            tb_mk,
            levels=[f * peak for f in CONTOURS_AIA],
            extent=m["extent"],
            origin="lower",
            colors="cyan",
            linewidths=0.8,
        )
        beam = (m["bmaj_deg"], m["bmin_deg"], m["bpa_deg"])
        _draw_disk(ax, beam, fov=FOV_AIA)
        ax.set_title(f"AIA 193 + {label} MHz", fontsize=10)

    fig.colorbar(last_im, ax=axes[:2, :].ravel().tolist(), pad=0.02, shrink=0.9).set_label(
        r"$T_B$ (MK)"
    )
    fig.suptitle(
        "Sharma & Oberoi 2020 Fig. 4  ·  2015-12-03 03:39–03:44 UT  ·  obsid 1133149192",
        fontsize=11,
    )
    fig.savefig(out, dpi=160)
    plt.close(fig)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
