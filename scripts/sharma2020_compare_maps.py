"""PNG comparison of the quiet-Sun maps. Open the PNG; do not open FITS.

    python scripts/sharma2020_compare_maps.py
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from astropy.io import fits
from astropy.wcs import FITSFixedWarning
from matplotlib.patches import Circle, Ellipse
import warnings

from solarburst.config import REPO_ROOT
from solarburst.maps import (
    frequency_hz,
    header_cell_arcsec,
    hpc_extent,
    jybeam_to_tb,
    load_casa_2d,
    solar_pixel,
)
from solarburst.mohan2017 import scale_image

warnings.filterwarnings("ignore", category=FITSFixedWarning)

RSUN = 958.0
FOV = 2500.0
NPIX = 100
BANDS = (
    ("108", "084-085", 108.14e6),
    ("162", "125-126", 160.62e6),
    ("217", "169-170", 216.94e6),
    ("240", "187-188", 239.98e6),
)
TABLE2 = {"108": 2.16, "162": 5.08, "217": 11.3, "240": 17.1}

ROW_LABELS = [
    "1. Rohit’s 4-minute average\n(same files as Figure 4,\nnot a photocopy of the journal)",
    "2. Same pictures as row 1,\nonly the colour numbers changed\n(whole-Sun brightness applied)",
    "3. We remade a 4-minute picture\nwith WSClean\n(not the program the paper used)",
    "4. One half-second snapshot\nmade with CASA\n(the program the paper used)",
    "5. The same half-second\nmade with WSClean\n(so 4 and 5 can be compared)",
]


def _crop_around_sun(data: np.ndarray, hdr: fits.Header, npix: int = NPIX):
    """Put the optical Sun at the crop centre — same rule as Figure 4."""
    sx, sy = solar_pixel(hdr)
    x0 = int(round(sx - (npix - 1) / 2.0))
    y0 = int(round(sy - (npix - 1) / 2.0))
    crop = data[y0 : y0 + npix, x0 : x0 + npix]
    if crop.shape != (npix, npix):
        raise ValueError(f"crop {crop.shape} from {data.shape} at ({x0},{y0}) sun=({sx:.1f},{sy:.1f})")
    extent = hpc_extent(
        npix, npix, cell_arcsec=header_cell_arcsec(hdr), sun_xy=(sx, sy), origin=(x0, y0)
    )
    return crop, extent, (float(hdr["BMAJ"]), float(hdr["BMIN"]), float(hdr.get("BPA", 0.0)))


def load_new_tb(path: Path) -> dict:
    data, hdr = load_casa_2d(path)
    crop, extent, beam = _crop_around_sun(data, hdr)
    nu = frequency_hz(hdr)
    tb = jybeam_to_tb(crop, nu, beam[0], beam[1], scale=1.0)
    hdr_c = hdr.copy()
    # CRPIX for the crop, used only by the flux-scale helper.
    sx, sy = solar_pixel(hdr)
    x0 = int(round(sx - (NPIX - 1) / 2.0))
    y0 = int(round(sy - (NPIX - 1) / 2.0))
    hdr_c["CRPIX1"] = float(hdr["CRPIX1"]) - x0
    hdr_c["CRPIX2"] = float(hdr["CRPIX2"]) - y0
    return {"tb": tb, "jy": crop, "header": hdr_c, "beam": beam, "freq_hz": nu, "extent": extent}


def load_rohit() -> dict[str, dict]:
    packed = np.load(REPO_ROOT / "data" / "quiet2015" / "fig4_means.npz")
    out = {}
    for lab, ch, nu in BANDS:
        hdr = fits.Header()
        hdr["BMAJ"] = float(packed[f"{ch}_bmaj"])
        hdr["BMIN"] = float(packed[f"{ch}_bmin"])
        hdr["BPA"] = float(packed[f"{ch}_bpa"])
        hdr["CDELT1"] = -50.0 / 3600.0
        hdr["CDELT2"] = 50.0 / 3600.0
        hdr["CRPIX1"] = (NPIX + 1) / 2.0
        hdr["CRPIX2"] = (NPIX + 1) / 2.0
        tb = np.asarray(packed[f"{ch}_tb"], dtype=np.float64)
        jy = tb / (jybeam_to_tb(np.ones(1), nu, hdr["BMAJ"], hdr["BMIN"], scale=9.48)[0])
        out[lab] = {
            "tb": tb,
            "jy": jy,
            "header": hdr,
            "beam": (hdr["BMAJ"], hdr["BMIN"], hdr["BPA"]),
            "freq_hz": nu,
            "extent": np.asarray(packed[f"{ch}_extent"], dtype=np.float64),
        }
    return out


def load_s_odot() -> dict[str, float]:
    flux_dir = REPO_ROOT / "data" / "quiet2015" / "paper_flux"
    return {
        lab: float(json.loads((flux_dir / f"{lab}MHz_full.json").read_text())["s_odot_sfu"])
        for lab, _ch, _nu in BANDS
    }


def draw(ax, tb, extent, beam, title, *, own_scale: bool) -> float:
    tb_mk = np.asarray(tb, dtype=np.float64) / 1e6
    peak = float(np.nanmax(tb_mk))
    if own_scale:
        cut = 0.12 * peak if peak > 0 else 0.0
        vmax = max(peak, 1e-6)
    else:
        cut = 0.2
        vmax = 1.7
    shown = np.where(tb_mk > cut, tb_mk, np.nan)
    ax.imshow(
        shown, origin="lower", extent=extent, cmap="jet",
        vmin=0.0, vmax=vmax, interpolation="nearest",
    )
    if peak > 0:
        ax.contour(
            tb_mk, levels=[f * peak for f in (0.70, 0.75, 0.80, 0.85, 0.90, 0.95)],
            extent=extent, origin="lower", colors="black", linewidths=0.6,
        )
    for r in (1.0, 2.0):
        ax.add_patch(Circle((0.0, 0.0), r * RSUN, fill=False, color="saddlebrown", lw=1.2))
    bmaj, bmin, bpa = beam
    ax.add_patch(
        Ellipse(
            (-0.80 * FOV, -0.80 * FOV),
            width=bmin * 3600.0, height=bmaj * 3600.0, angle=-bpa,
            fill=False, color="black", lw=1.0,
        )
    )
    ax.set_xlim(-FOV, FOV)
    ax.set_ylim(-FOV, FOV)
    ax.set_aspect("equal")
    ax.tick_params(labelsize=7)
    ax.set_title(title, fontsize=10)
    ax.text(
        0.03, 0.97, f"peak {peak:.2f} million K",
        transform=ax.transAxes, va="top", fontsize=8, color="white",
        bbox=dict(boxstyle="round,pad=0.15", fc="black", alpha=0.45, lw=0),
    )
    return peak


def main() -> int:
    outdir = REPO_ROOT / "figures" / "sharma2020"
    outdir.mkdir(parents=True, exist_ok=True)
    rohit = load_rohit()
    s_odot = load_s_odot()
    wsclean = {
        lab: load_new_tb(REPO_ROOT / "data" / "quiet2015" / "wsclean" / f"{lab}MHz-image.fits")
        for lab, _ch, _nu in BANDS
    }
    casa = {
        lab: load_new_tb(REPO_ROOT / "data" / "quiet2015" / "paper_casa" / f"{lab}MHz_mid.fits")
        for lab, _ch, _nu in BANDS
    }
    wsnap = {
        lab: load_new_tb(
            REPO_ROOT / "data" / "quiet2015" / "paper_wsclean" / f"{lab}MHz_mid-image.fits"
        )
        for lab, _ch, _nu in BANDS
    }
    paper = {}
    print(f"{'band':5s} {'row1 MK':>8s} {'row2 MK':>8s} {'row3 MK':>8s} {'row4 MK':>8s}")
    for lab, _ch, _nu in BANDS:
        rec = scale_image(
            rohit[lab]["jy"], rohit[lab]["header"], s_odot[lab] * 1e4,
            nsig=5.0, freq_hz=rohit[lab]["freq_hz"],
        )
        rec["beam"] = rohit[lab]["beam"]
        rec["extent"] = rohit[lab]["extent"]
        paper[lab] = rec
        print(
            f"{lab:5s} {rohit[lab]['tb'].max()/1e6:8.3f} {rec['tb_K'].max()/1e6:8.3f} "
            f"{wsclean[lab]['tb'].max()/1e6:8.3f} {casa[lab]['tb'].max()/1e6:8.3f}"
        )

    rows = [
        {lab: rohit[lab] for lab, *_ in BANDS},
        {lab: {"tb": paper[lab]["tb_K"], "beam": paper[lab]["beam"], "extent": paper[lab]["extent"]} for lab, *_ in BANDS},
        wsclean,
        casa,
        wsnap,
    ]
    own_scale = [False, True, True, True, True]

    fig, axes = plt.subplots(len(rows), 4, figsize=(13.0, 15.2))
    fig.subplots_adjust(left=0.26, right=0.99, top=0.91, bottom=0.04, hspace=0.32, wspace=0.10)
    for i, maps in enumerate(rows):
        for j, (lab, *_rest) in enumerate(BANDS):
            ax = axes[i, j]
            m = maps[lab]
            draw(
                ax, m["tb"], m["extent"], m["beam"],
                f"{lab} MHz" if i == 0 else "",
                own_scale=own_scale[i],
            )
            ax.set_xlabel("distance from Sun centre (arcsec)" if i == len(rows) - 1 else "", fontsize=8)
            ax.set_ylabel("" if j else "distance from Sun centre (arcsec)", fontsize=8)
            if j > 0:
                ax.set_yticklabels([])
        axes[i, 0].text(
            -0.62, 0.5, ROW_LABELS[i],
            transform=axes[i, 0].transAxes, ha="right", va="center", fontsize=9,
        )

    fig.suptitle(
        "Same quiet Sun, 3 December 2015, 03:39–03:44 UT\n"
        "Brown rings = 1× and 2× the optical solar radius, centred on the Sun.\n"
        "Row 1 colour bar is 0–1.7 million K (as in Figure 4). "
        "Rows 2–5 each run from 0 to that panel’s own peak, so the shape is visible.",
        fontsize=11,
    )
    maps_png = outdir / "compare_maps.png"
    fig.savefig(maps_png, dpi=140)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8.2, 4.6), layout="constrained")
    x = np.arange(len(BANDS))
    ours = [s_odot[lab] for lab, *_ in BANDS]
    ref = [TABLE2[lab] for lab, *_ in BANDS]
    ax.bar(x - 0.18, ours, 0.36, color="steelblue", label="3 Dec 2015 — measured from this observation")
    ax.bar(x + 0.18, ref, 0.36, color="0.75", label="3 Sep 2013 — a different quiet day, rough check only")
    ax.set_xticks(x, [f"{lab} MHz" for lab, *_ in BANDS])
    ax.set_ylabel("Brightness of the whole Sun")
    ax.set_title("Whole-Sun radio brightness (the number used to recolour row 2)")
    ax.legend(frameon=False, fontsize=9)
    ax.set_ylim(0, 20)
    for i, v in enumerate(ours):
        ax.text(i - 0.18, v + 0.3, f"{v:.1f}", ha="center", fontsize=8)
    flux_png = outdir / "compare_flux.png"
    fig.savefig(flux_png, dpi=140)
    plt.close(fig)
    print(f"wrote {maps_png}")
    print(f"wrote {flux_png}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
