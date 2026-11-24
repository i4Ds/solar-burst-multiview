#!/usr/bin/env python3
"""CASA remake: SuperUniform imaging with the Figure 4 numbers.

Calibration: the published phase-only Cen A bandpass tables, CASA
applycal (applymode=calonly, calwt=False). Imaging: CASA 6.6 tclean,
SuperUniform, Hogbom, 8000 iterations, 1024² × 50″, 0.5 s. Flux: Oberoi
2017 whole-Sun S_⊙ with Haslam 1982 at this pointing. Scale: Mohan F(ν)
at 5σ on each frame, then the time mean.

Laptop path (this file): read FITS already imaged on calculon, apply
Mohan, plot. Cluster imaging: scripts/calculon/quiet_noon_casa_snap.py
and scripts/calculon/sharma2020_casa_snap.py.

    python scripts/pipelines/casa_remake.py --demo
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle, Ellipse

from solarburst.config import REPO_ROOT
from solarburst.maps import (
    crop_around_sun,
    frequency_hz,
    header_cell_arcsec,
    hpc_extent,
    load_casa_2d,
)
from solarburst.mohan2017 import scale_image
from solarburst.sharma2020 import CLEAN, NPIX, NSIG

# Same SuperUniform numbers as the published FITS HISTORY. This
# installation images with tclean (CASA 6.6).
IMAGING = dict(CLEAN)
IMAGING["task"] = "tclean"
IMAGING["casa_version"] = "6.6"

FRAMES = REPO_ROOT / "data" / "quiet2015" / "paper_casa_su"
FLUX_DIR = REPO_ROOT / "data" / "quiet2015" / "paper_flux"
MEAN_CACHE = REPO_ROOT / "data" / "quiet2015" / "fig4_ours_tb.npz"
OUTDIR = REPO_ROOT / "figures" / "pipelines"
RSUN, FOV = 958.0, 2500.0
CONTOURS = (0.70, 0.75, 0.80, 0.85, 0.90, 0.95)
BANDS = ("108", "162", "217", "240")
OBS_TIME = "3 December 2015, 03:39–03:44 UT"

# Cluster imaging for other quiet noon scans (same SuperUniform numbers,
# phase centre from that observation's metafits).
CLUSTER_SNAP = "scripts/calculon/quiet_noon_casa_snap.py"
CLUSTER_MEAN = "scripts/calculon/quiet_noon_mean_tb.py"


def s_odot_jy(lab: str) -> float:
    rec = json.loads((FLUX_DIR / f"{lab}MHz_full.json").read_text())
    return float(rec["s_odot_jy"])


def list_frames(lab: str, directory: Path | None = None) -> list[Path]:
    d = directory or FRAMES
    return sorted(d.glob(f"{lab}MHz_*.fits"))


def one_frame(lab: str, index: str = "0306") -> Path:
    path = FRAMES / f"{lab}MHz_{index}.fits"
    if not path.exists():
        raise FileNotFoundError(path)
    return path


def scale_frame(path: Path, s_odot: float, *, nsig: float = NSIG) -> dict:
    data, hdr = load_casa_2d(path)
    crop, origin, sun = crop_around_sun(data, hdr, NPIX)
    hdr_c = hdr.copy()
    hdr_c["CRPIX1"] = (NPIX + 1) / 2.0
    hdr_c["CRPIX2"] = (NPIX + 1) / 2.0
    rec = scale_image(crop, hdr_c, s_odot, nsig=nsig, freq_hz=frequency_hz(hdr))
    rec["extent"] = np.asarray(
        hpc_extent(NPIX, NPIX, cell_arcsec=header_cell_arcsec(hdr), sun_xy=sun, origin=origin)
    )
    rec["bmaj_deg"] = float(hdr["BMAJ"])
    rec["bmin_deg"] = float(hdr["BMIN"])
    rec["bpa_deg"] = float(hdr.get("BPA", 0.0))
    rec["header"] = hdr
    rec["jybeam_raw"] = crop
    rec["freq_hz"] = frequency_hz(hdr)
    return rec


def load_mean(lab: str) -> dict:
    z = np.load(MEAN_CACHE)
    return {
        "tb": z[f"{lab}_tb"],
        "extent": z[f"{lab}_extent"],
        "bmaj_deg": float(z[f"{lab}_bmaj_deg"]),
        "bmin_deg": float(z[f"{lab}_bmin_deg"]),
        "bpa_deg": float(z[f"{lab}_bpa_deg"]),
        "n": int(z[f"{lab}_n"]),
        "f_nu_mean": float(z[f"{lab}_f_nu_mean"]),
    }


def show_tb(ax, tb_k, extent, beam, title: str) -> float:
    tb = np.asarray(tb_k, dtype=np.float64) / 1e6
    peak = float(np.nanmax(tb))
    cut = 0.12 * peak if peak > 0 else 0.0
    shown = np.where(tb > cut, tb, np.nan)
    ax.imshow(
        shown,
        origin="lower",
        extent=extent,
        cmap="jet",
        vmin=0.0,
        vmax=max(peak, 1e-6),
        interpolation="nearest",
    )
    if peak > 0:
        ax.contour(
            tb,
            levels=[f * peak for f in CONTOURS],
            extent=extent,
            origin="lower",
            colors="black",
            linewidths=0.6,
        )
    for r in (1, 2):
        ax.add_patch(Circle((0, 0), r * RSUN, fill=False, color="brown", lw=1.3))
    bmaj, bmin, bpa = beam
    ax.add_patch(
        Ellipse((-2000, -2000), bmin * 3600, bmaj * 3600, angle=-bpa, fill=False, color="black", lw=1.0)
    )
    ax.set_xlim(-FOV, FOV)
    ax.set_ylim(-FOV, FOV)
    ax.set_aspect("equal")
    ax.set_title(title, fontsize=11)
    ax.set_xlabel("Solar X (arcsec)", fontsize=8)
    ax.tick_params(labelsize=8)
    ax.text(
        0.03,
        0.97,
        f"{peak:.2f} MK",
        transform=ax.transAxes,
        va="top",
        fontsize=9,
        color="white",
        bbox=dict(boxstyle="round,pad=0.15", fc="black", alpha=0.45, lw=0),
    )
    return peak


def demo(out: Path | None = None) -> Path:
    lab = "108"
    path = one_frame(lab)
    sodot = s_odot_jy(lab)
    frame = scale_frame(path, sodot)
    mean = load_mean(lab)
    n_disk = len(list_frames(lab))
    out = out or OUTDIR / "casa_remake_demo.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 3, figsize=(13.2, 4.0), constrained_layout=True)
    axes[0].imshow(frame["jybeam_raw"], origin="lower", extent=frame["extent"], cmap="gray")
    axes[0].set_title("CASA 6.6 tclean 0.5 s, Jy/beam")
    axes[0].set_xlabel("Solar X (arcsec)", fontsize=8)
    axes[0].set_ylabel("Solar Y (arcsec)", fontsize=8)
    show_tb(
        axes[1],
        frame["tb_K"],
        frame["extent"],
        (frame["bmaj_deg"], frame["bmin_deg"], frame["bpa_deg"]),
        f"Mohan F(ν) = {frame['f_nu']:.1f}",
    )
    show_tb(
        axes[2],
        mean["tb"],
        mean["extent"],
        (mean["bmaj_deg"], mean["bmin_deg"], mean["bpa_deg"]),
        f"Time mean, n = {mean['n']} / {n_disk}",
    )
    for ax in axes:
        ax.set_xlim(-FOV, FOV)
        ax.set_ylim(-FOV, FOV)
        ax.set_aspect("equal")
    fig.suptitle(
        f"CASA remake  ·  {OBS_TIME}  ·  {lab} MHz  ·  SuperUniform Hogbom 8000  ·  "
        f"S_⊙ = {sodot/1e4:.2f} SFU",
        fontsize=11,
    )
    fig.savefig(out, dpi=140, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {out}")
    print(f"frames on disk {n_disk}  F(ν) {frame['f_nu']:.2f}  beam "
          f"{frame['bmaj_deg']*3600:.0f}″×{frame['bmin_deg']*3600:.0f}″")
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--demo", action="store_true")
    args = p.parse_args(argv)
    print("Imaging (CASA remake):")
    for k, v in IMAGING.items():
        print(f"  {k:16s} {v}")
    print(f"cluster snap  {CLUSTER_SNAP}")
    print(f"cluster mean  {CLUSTER_MEAN}")
    demo()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
