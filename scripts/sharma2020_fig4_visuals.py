#!/usr/bin/env python3
"""Wall of maps: Sharma 2020 Fig. 4 vs our SuperUniform remake.

Writes PNGs under figures/sharma2020/. Does not touch fig4.png.
Re-run after more frames land in data/quiet2015/paper_casa_su/.

    python scripts/sharma2020_fig4_visuals.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from astropy.wcs import FITSFixedWarning
from matplotlib.patches import Circle, Ellipse
import warnings

from solarburst.config import REPO_ROOT
from solarburst.maps import (
    crop_around_sun,
    frequency_hz,
    header_cell_arcsec,
    hpc_extent,
    load_casa_2d,
)
from solarburst.mohan2017 import scale_image
from solarburst.sharma2020 import NPIX, NSIG, _crop_header

warnings.filterwarnings("ignore", category=FITSFixedWarning)

RSUN = 958.0
FOV = 2500.0
VMAX = 1.7
CUT_MK = 0.2
CONTOURS = (0.70, 0.75, 0.80, 0.85, 0.90, 0.95)
BANDS = ("108", "162", "217", "240")
CAPTION = {"108": 0.92, "162": 1.20, "217": 1.50, "240": None}

HIS_NPZ = REPO_ROOT / "data" / "quiet2015" / "fig4_tb_perframe.npz"
OURS_DIR = REPO_ROOT / "data" / "quiet2015" / "paper_casa_su"
FLUX_DIR = REPO_ROOT / "data" / "quiet2015" / "paper_flux"
OUTDIR = REPO_ROOT / "figures" / "sharma2020"
CACHE = REPO_ROOT / "data" / "quiet2015" / "fig4_ours_tb.npz"
SUMMARY = REPO_ROOT / "figures" / "sharma2020" / "fig4_ours_summary.json"


def our_frames(lab: str) -> list[Path]:
    rx = re.compile(rf"^{lab}MHz_(\d{{4}})\.fits$")
    return [p for p in sorted(OURS_DIR.glob(f"{lab}MHz_*.fits")) if rx.match(p.name)]


def s_odot_jy(lab: str) -> float:
    rec = json.loads((FLUX_DIR / f"{lab}MHz_full.json").read_text())
    return float(rec["s_odot_jy"])


def mean_tb_paths(paths: list[Path], s_jy: float) -> dict:
    data0, hdr0 = load_casa_2d(paths[0])
    crop0, origin, sun = crop_around_sun(data0, hdr0, NPIX)
    y0, x0 = origin[1], origin[0]
    extent = hpc_extent(
        NPIX, NPIX, cell_arcsec=header_cell_arcsec(hdr0), sun_xy=sun, origin=origin
    )
    acc = np.zeros_like(crop0, dtype=np.float64)
    f_nu: list[float] = []
    beams: list[tuple[float, float, float]] = []
    freq = frequency_hz(hdr0)
    for i, path in enumerate(paths):
        data, hdr = load_casa_2d(path)
        crop = data[y0 : y0 + NPIX, x0 : x0 + NPIX]
        rec = scale_image(
            crop, _crop_header(hdr, NPIX), s_jy, nsig=NSIG, freq_hz=frequency_hz(hdr)
        )
        acc += rec["tb_K"]
        f_nu.append(float(rec["f_nu"]))
        beams.append((float(hdr["BMAJ"]), float(hdr["BMIN"]), float(hdr.get("BPA", 0.0))))
        if (i + 1) % 50 == 0 or i + 1 == len(paths):
            print(f"  {path.name[:3]}  {i + 1}/{len(paths)}  F(ν)={f_nu[-1]:.2f}", flush=True)
    mean = acc / len(paths)
    bmaj, bmin, bpa = np.median(np.asarray(beams), axis=0)
    f = np.asarray(f_nu, dtype=np.float64)
    return {
        "tb": mean.astype(np.float32),
        "extent": np.asarray(extent, dtype=np.float64),
        "beam": (float(bmaj), float(bmin), float(bpa)),
        "n": len(paths),
        "freq_hz": float(freq),
        "f_nu_mean": float(np.mean(f)),
        "f_nu_std": float(np.std(f)),
        "kind": "mean",
    }


def load_one(path: Path, s_jy: float) -> dict:
    data, hdr = load_casa_2d(path)
    crop, origin, sun = crop_around_sun(data, hdr, NPIX)
    extent = hpc_extent(
        NPIX, NPIX, cell_arcsec=header_cell_arcsec(hdr), sun_xy=sun, origin=origin
    )
    rec = scale_image(
        crop, _crop_header(hdr, NPIX), s_jy, nsig=NSIG, freq_hz=frequency_hz(hdr)
    )
    return {
        "tb": rec["tb_K"].astype(np.float32),
        "extent": np.asarray(extent, dtype=np.float64),
        "beam": (float(hdr["BMAJ"]), float(hdr["BMIN"]), float(hdr.get("BPA", 0.0))),
        "n": 1,
        "freq_hz": float(rec["freq_hz"]),
        "f_nu_mean": float(rec["f_nu"]),
        "f_nu_std": 0.0,
        "kind": "snapshot",
        "name": path.name,
    }


def load_ours() -> dict[str, dict]:
    cached: dict[str, dict] = {}
    if CACHE.exists():
        z = np.load(CACHE, allow_pickle=False)
        for lab in BANDS:
            key = f"{lab}_n"
            if key not in z:
                continue
            cached[lab] = {
                "tb": z[f"{lab}_tb"],
                "extent": z[f"{lab}_extent"],
                "beam": (
                    float(z[f"{lab}_bmaj_deg"]),
                    float(z[f"{lab}_bmin_deg"]),
                    float(z[f"{lab}_bpa_deg"]),
                ),
                "n": int(z[f"{lab}_n"]),
                "freq_hz": float(z[f"{lab}_freq_hz"]),
                "f_nu_mean": float(z[f"{lab}_f_nu_mean"]),
                "f_nu_std": float(z[f"{lab}_f_nu_std"]),
                "kind": "mean" if int(z[f"{lab}_n"]) > 1 else "snapshot",
            }

    packed: dict[str, np.ndarray | str] = {}
    ours: dict[str, dict] = {}
    for lab in BANDS:
        paths = our_frames(lab)
        n = len(paths)
        mid = OURS_DIR / f"{lab}MHz_mid.fits"
        if lab in cached and cached[lab]["n"] == n and n > 0:
            print(f"{lab} MHz  reuse cache n={n}", flush=True)
            ours[lab] = cached[lab]
        elif n >= 3:
            print(f"{lab} MHz  mean of {n} frames", flush=True)
            ours[lab] = mean_tb_paths(paths, s_odot_jy(lab))
        elif mid.exists():
            print(f"{lab} MHz  only mid-scan snapshot (n={n} numbered)", flush=True)
            ours[lab] = load_one(mid, s_odot_jy(lab))
        else:
            print(f"{lab} MHz  no remake yet", flush=True)
            continue
        rec = ours[lab]
        packed[f"{lab}_tb"] = rec["tb"]
        packed[f"{lab}_extent"] = rec["extent"]
        packed[f"{lab}_bmaj_deg"] = np.float64(rec["beam"][0])
        packed[f"{lab}_bmin_deg"] = np.float64(rec["beam"][1])
        packed[f"{lab}_bpa_deg"] = np.float64(rec["beam"][2])
        packed[f"{lab}_n"] = np.int32(rec["n"])
        packed[f"{lab}_freq_hz"] = np.float64(rec["freq_hz"])
        packed[f"{lab}_f_nu_mean"] = np.float64(rec["f_nu_mean"])
        packed[f"{lab}_f_nu_std"] = np.float64(rec["f_nu_std"])
    if packed:
        np.savez_compressed(CACHE, **packed)
    return ours


def load_his() -> dict[str, dict]:
    z = np.load(HIS_NPZ)
    out = {}
    for lab in BANDS:
        out[lab] = {
            "tb": z[f"{lab}_tb"],
            "extent": z[f"{lab}_extent"],
            "beam": (
                float(z[f"{lab}_bmaj_deg"]),
                float(z[f"{lab}_bmin_deg"]),
                float(z[f"{lab}_bpa_deg"]),
            ),
            "n": 570,
            "kind": "mean",
        }
    return out


def sun_rings(ax) -> None:
    ax.add_patch(Circle((0, 0), RSUN, fill=False, color="saddlebrown", lw=1.3))
    ax.add_patch(
        Circle((0, 0), 2 * RSUN, fill=False, color="saddlebrown", lw=0.9, ls="--")
    )
    ax.set_xlim(-FOV, FOV)
    ax.set_ylim(-FOV, FOV)
    ax.set_aspect("equal")
    ax.tick_params(labelsize=8)


def show_tb(ax, rec: dict, title: str, *, vmax: float | None, colorbar: bool = False):
    tb_mk = np.asarray(rec["tb"], dtype=float) / 1e6
    peak = float(np.nanmax(tb_mk))
    if vmax is None:
        cut = 0.12 * peak if peak > 0 else 0.0
        vmax_use = max(peak, 1e-6)
    else:
        cut = CUT_MK
        vmax_use = vmax
    shown = np.where(tb_mk > cut, tb_mk, np.nan)
    im = ax.imshow(
        shown,
        origin="lower",
        extent=rec["extent"],
        cmap="jet",
        vmin=0.0,
        vmax=vmax_use,
        interpolation="nearest",
    )
    if peak > 0:
        ax.contour(
            tb_mk,
            levels=[f * peak for f in CONTOURS],
            extent=rec["extent"],
            origin="lower",
            colors="black",
            linewidths=0.6,
        )
    sun_rings(ax)
    bmaj, bmin, bpa = rec["beam"]
    ax.add_patch(
        Ellipse(
            (-0.78 * FOV, -0.78 * FOV),
            width=bmin * 3600.0,
            height=bmaj * 3600.0,
            angle=-bpa,
            fill=False,
            color="k",
            lw=1.0,
        )
    )
    ax.set_title(title, fontsize=11)
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
    if colorbar:
        cb = ax.figure.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        cb.set_label("million K", fontsize=8)
        cb.ax.tick_params(labelsize=8)
    return im, peak


def ours_title(lab: str, rec: dict) -> str:
    if rec["kind"] == "snapshot":
        return f"ours  {lab} MHz  mid-scan"
    return f"ours  {lab} MHz  {rec['n']}/570"


def save(fig, name: str) -> Path:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    path = OUTDIR / name
    fig.savefig(path, dpi=140, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {path}", flush=True)
    return path


def panel_his_row(his: dict, *, vmax: float | None, name: str, subtitle: str) -> None:
    fig, axes = plt.subplots(1, 4, figsize=(14.8, 3.9), constrained_layout=True)
    last = None
    for ax, lab in zip(axes, BANDS):
        cap = CAPTION[lab]
        title = f"his  {lab} MHz" + (f"  caption {cap:.2f}" if cap else "")
        last, _ = show_tb(ax, his[lab], title, vmax=vmax)
        ax.set_xlabel("Solar X (arcsec)", fontsize=8)
        ax.set_ylabel("Solar Y (arcsec)" if ax is axes[0] else "", fontsize=8)
        if ax is not axes[0]:
            ax.set_yticklabels([])
    fig.colorbar(last, ax=axes, fraction=0.02, pad=0.01).set_label("million K")
    fig.suptitle(subtitle, fontsize=12)
    save(fig, name)


def two_row(his: dict, ours: dict, *, vmax: float | None, name: str, subtitle: str) -> None:
    fig, axes = plt.subplots(2, 4, figsize=(14.8, 7.6), constrained_layout=True)
    last = None
    for j, lab in enumerate(BANDS):
        last, _ = show_tb(axes[0, j], his[lab], f"his  {lab} MHz  570 frames", vmax=vmax)
        if lab in ours:
            show_tb(axes[1, j], ours[lab], ours_title(lab, ours[lab]), vmax=vmax)
        else:
            axes[1, j].set_title(f"ours  {lab} MHz  not yet")
            axes[1, j].axis("off")
        axes[1, j].set_xlabel("Solar X (arcsec)", fontsize=8)
        axes[0, j].set_xticklabels([])
        if j:
            axes[0, j].set_yticklabels([])
            axes[1, j].set_yticklabels([])
        else:
            axes[0, j].set_ylabel("Solar Y (arcsec)", fontsize=8)
            axes[1, j].set_ylabel("Solar Y (arcsec)", fontsize=8)
    if vmax is not None and last is not None:
        fig.colorbar(last, ax=axes, fraction=0.02, pad=0.01).set_label("million K")
    fig.suptitle(subtitle, fontsize=12)
    save(fig, name)


def diff_row(his: dict, ours: dict) -> None:
    fig, axes = plt.subplots(1, 4, figsize=(14.8, 3.9), constrained_layout=True)
    last = None
    for ax, lab in zip(axes, BANDS):
        if lab not in ours:
            ax.axis("off")
            continue
        d = (np.asarray(ours[lab]["tb"]) - np.asarray(his[lab]["tb"])) / 1e6
        span = max(float(np.nanmax(np.abs(d))), 0.02)
        last = ax.imshow(
            d,
            origin="lower",
            extent=his[lab]["extent"],
            cmap="RdBu_r",
            vmin=-span,
            vmax=span,
            interpolation="nearest",
        )
        sun_rings(ax)
        peak = float(np.nanmax(np.abs(d)))
        ax.set_title(f"{lab} MHz  ours − his")
        ax.text(
            0.03,
            0.97,
            f"max |Δ| {peak:.2f} MK",
            transform=ax.transAxes,
            va="top",
            fontsize=8,
            color="k",
        )
        ax.set_xlabel("Solar X (arcsec)", fontsize=8)
        ax.set_ylabel("Solar Y (arcsec)" if ax is axes[0] else "", fontsize=8)
        if ax is not axes[0]:
            ax.set_yticklabels([])
    if last is not None:
        fig.colorbar(last, ax=axes, fraction=0.02, pad=0.01).set_label("million K")
    fig.suptitle("Ours minus his, each panel stretched to its own ±max. Red = we are hotter.")
    save(fig, "fig4_diff.png")


def filmstrip(lab: str, s_jy: float, n_pick: int = 8) -> None:
    paths = our_frames(lab)
    if len(paths) < 4:
        mid = OURS_DIR / f"{lab}MHz_mid.fits"
        if not mid.exists():
            print(f"no filmstrip for {lab}", flush=True)
            return
        paths = [mid]
    pick = [paths[i] for i in np.linspace(0, len(paths) - 1, min(n_pick, len(paths)), dtype=int)]
    nrow = 2 if len(pick) > 4 else 1
    ncol = int(np.ceil(len(pick) / nrow))
    fig, axes = plt.subplots(nrow, ncol, figsize=(3.6 * ncol, 3.7 * nrow), constrained_layout=True)
    axes_list = np.atleast_1d(axes).ravel()
    last = None
    for ax, path in zip(axes_list, pick):
        rec = load_one(path, s_jy)
        last, _ = show_tb(ax, rec, path.name.replace(".fits", ""), vmax=VMAX)
        ax.set_xlabel("")
        ax.set_ylabel("")
        ax.set_xticklabels([])
        ax.set_yticklabels([])
    for ax in axes_list[len(pick) :]:
        ax.axis("off")
    if last is not None:
        fig.colorbar(last, ax=axes_list[: len(pick)].tolist(), fraction=0.02, pad=0.01).set_label(
            "million K"
        )
    fig.suptitle(f"Our {lab} MHz half-second frames (sample of {len(paths)} on disk)", fontsize=12)
    save(fig, f"fig4_ours_strip_{lab}.png")


def write_summary(his: dict, ours: dict) -> None:
    rows = []
    for lab in BANDS:
        hpeak = float(np.nanmax(np.asarray(his[lab]["tb"]) / 1e6))
        rec = {
            "mhz": lab,
            "caption_mk": CAPTION[lab],
            "his_peak_mk": round(hpeak, 3),
            "his_beam_arcsec": [
                round(his[lab]["beam"][0] * 3600, 1),
                round(his[lab]["beam"][1] * 3600, 1),
            ],
        }
        if lab in ours:
            o = ours[lab]
            rec.update(
                {
                    "ours_n": o["n"],
                    "ours_kind": o["kind"],
                    "ours_peak_mk": round(float(np.nanmax(np.asarray(o["tb"]) / 1e6)), 3),
                    "ours_f_nu": round(o["f_nu_mean"], 2),
                    "ours_beam_arcsec": [
                        round(o["beam"][0] * 3600, 1),
                        round(o["beam"][1] * 3600, 1),
                    ],
                }
            )
        rows.append(rec)
        print(
            f"{lab:>3} MHz  his {hpeak:.2f} MK  "
            + (
                f"ours {rec['ours_peak_mk']:.2f} MK  n={rec['ours_n']}  "
                f"beam {rec['ours_beam_arcsec'][0]:.0f}″ vs his {rec['his_beam_arcsec'][0]:.0f}″"
                if lab in ours
                else "ours missing"
            ),
            flush=True,
        )
    SUMMARY.write_text(json.dumps(rows, indent=2) + "\n")


def main() -> int:
    his = load_his()
    ours = load_ours()
    write_summary(his, ours)
    panel_his_row(
        his,
        vmax=VMAX,
        name="fig4_his_mean.png",
        subtitle="Rohit · mean of 570 frames · paper flux · 0–1.7 million K",
    )
    two_row(
        his,
        ours,
        vmax=VMAX,
        name="fig4_his_vs_ours.png",
        subtitle="Same colour scale as the paper (0–1.7 million K). Top = his 570-frame mean. Bottom = our remake.",
    )
    two_row(
        his,
        ours,
        vmax=None,
        name="fig4_his_vs_ours_shape.png",
        subtitle="Each panel stretched to its own peak — look at shape, ignore the kelvin number.",
    )
    fig, axes = plt.subplots(1, 4, figsize=(14.8, 3.9), constrained_layout=True)
    last = None
    for ax, lab in zip(axes, BANDS):
        if lab not in ours:
            ax.axis("off")
            continue
        last, _ = show_tb(ax, ours[lab], ours_title(lab, ours[lab]), vmax=None)
        ax.set_xlabel("Solar X (arcsec)", fontsize=8)
        ax.set_ylabel("Solar Y (arcsec)" if ax is axes[0] else "", fontsize=8)
        if ax is not axes[0]:
            ax.set_yticklabels([])
    fig.suptitle("Our remake · mean of frames on disk · each panel its own peak")
    save(fig, "fig4_ours_mean.png")
    diff_row(his, ours)
    for lab in BANDS:
        filmstrip(lab, s_odot_jy(lab))
    return 0


if __name__ == "__main__":
    sys.exit(main())
