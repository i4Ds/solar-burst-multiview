"""Reproduce Sharma et al. 2022 figures from staged images and pickles.

    python -m solarburst.figures          # fig 3 and fig 5
    python -m solarburst.figures --fig 3
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap, LogNorm, TwoSlopeNorm
from matplotlib.patches import Circle

from solarburst.bursts import BurstMaps, detect
from solarburst.config import DATA_DIR, REPO_ROOT, load, local_path
from solarburst.maps import (
    aia_hpc_cutout,
    load_sharma_pickle,
    load_sub_cube,
    pickle_hpc_extent,
    pixels_per_beam,
    residual_tb_frame,
    time_reduce_tb,
)


def _figure_cfg(cfg: dict) -> dict:
    return cfg.get("figures", {})


def _tb_dir(cfg: dict) -> Path:
    return local_path(cfg, cfg["remote"]["paths"]["brightness_temp"])


def _output_dir(cfg: dict) -> Path:
    spec = _figure_cfg(cfg)
    raw = spec.get("output_dir", "figures/sharma2022")
    path = Path(raw)
    if not path.is_absolute():
        path = REPO_ROOT / path
    path.mkdir(parents=True, exist_ok=True)
    return path


def _published_bands(cfg: dict) -> list[dict]:
    skip = set(_figure_cfg(cfg).get("fig3", {}).get("omit_channels", ["125-126"]))
    return [b for b in cfg["bands"] if b["channels"] not in skip]


def _limb(ax, radius_arcsec: float) -> None:
    ax.add_patch(
        Circle((0.0, 0.0), radius_arcsec, fill=False, color="black", lw=0.9)
    )


def _style_hpc(ax, fov: float) -> None:
    ax.set_xlim(-fov, fov)
    ax.set_ylim(-fov, fov)
    ax.set_aspect("equal")
    ax.set_xlabel("Solar X (arcsec)")
    ax.set_ylabel("Solar Y (arcsec)")
    ax.tick_params(direction="in", length=3)


def fig3(cfg: dict, dest: Path | None = None) -> Path:
    """Time-median T_B maps, eight published bands (paper Figure 3)."""
    fcfg = _figure_cfg(cfg)
    f3 = fcfg.get("fig3", {})
    tbdir = _tb_dir(cfg)
    skip = f3.get("skip_obsids", [1133149192])
    how = f3.get("reduce", "median")
    vmax = float(f3.get("vmax_mk", 0.40))
    fov = float(fcfg.get("fov_arcsec", 2000))
    limb = float(fcfg.get("limb_arcmin", 16.0)) * 60.0
    cmap = fcfg.get("cmap", "jet")
    paper_peaks = list(f3.get("paper_peak_mk", []))
    paper_mhz = list(f3.get("paper_mhz", []))
    bands = _published_bands(cfg)
    extent = pickle_hpc_extent(
        cell_arcsec=float(cfg["imaging"]["cell_arcsec"]),
    )

    maps = []
    peaks = []
    for band in bands:
        path = tbdir / f"Tb_20151203_{band['channels']}.p"
        print(f"fig3  {band['label']:7s}  {path.name}", file=sys.stderr)
        tb = time_reduce_tb(path, skip_obsids=skip, how=how)
        maps.append(tb)
        peaks.append(float(np.nanmax(tb)) / 1e6)

    fig, axes = plt.subplots(2, 4, figsize=(12.4, 6.2), sharex=True, sharey=True)
    last_im = None
    for i, (ax, band, tb, peak) in enumerate(zip(axes.ravel(), bands, maps, peaks)):
        last_im = ax.imshow(
            tb / 1e6,
            origin="lower",
            extent=extent,
            cmap=cmap,
            vmin=0.0,
            vmax=vmax,
            interpolation="nearest",
        )
        _limb(ax, limb)
        _style_hpc(ax, fov)
        mhz = paper_mhz[i] if i < len(paper_mhz) else int(round(band["freq_mhz"]))
        ax.set_title(f"{mhz} MHz   {peak:.2f} MK", fontsize=9, pad=3)
    for ax in axes[:, 1:].ravel():
        ax.set_ylabel("")
    for ax in axes[0]:
        ax.set_xlabel("")

    fig.subplots_adjust(left=0.06, right=0.90, top=0.92, bottom=0.10, wspace=0.08, hspace=0.18)
    cax = fig.add_axes([0.92, 0.12, 0.015, 0.76])
    cb = fig.colorbar(last_im, cax=cax)
    cb.set_label(r"$T_B$ (MK)")

    dest = dest or _output_dir(cfg) / "fig3.png"
    fig.savefig(dest, dpi=160)
    plt.close(fig)

    print(f"{'band':8s} {'peak MK':>8s} {'paper':>6s} {'ratio':>6s}")
    ok = True
    for band, peak, paper in zip(
        bands, peaks, paper_peaks + [float("nan")] * len(bands)
    ):
        ratio = peak / paper if paper else float("nan")
        print(f"{band['channels']:8s} {peak:8.3f} {paper:6.2f} {ratio:6.3f}")
        if paper and not (0.85 <= ratio <= 1.15):
            ok = False
    print(f"wrote {dest}")
    if not ok:
        print("GATE WARNING: a peak is more than 15% from the paper", file=sys.stderr)
    else:
        print("GATE: peak T_B within 15% of Figure 3 caption")
    return dest


def fig5(cfg: dict, dest: Path | None = None) -> Path:
    """Residual T_B overlay at 03:24:36.5–37.0 UT (paper Figure 5)."""
    fcfg = _figure_cfg(cfg)
    f5 = fcfg.get("fig5", {})
    tbdir = _tb_dir(cfg)
    fov = float(fcfg.get("fov_fig5_arcsec", fcfg.get("fov_arcsec", 2000) + 500))
    limb = float(fcfg.get("limb_arcmin", 16.0)) * 60.0
    contour_k = float(f5.get("contour_k", 2.0e4))
    threshold_k = float(f5.get("residual_threshold_k", 4500.0))
    mask_disk = bool(f5.get("mask_outside_radio_sun", True))
    frame = int(f5.get("frame", 0))
    channels = list(f5.get("channels", ["084-085", "139-140", "187-188"]))
    colors = list(f5.get("colors", ["#d62728", "#2ca02c", "#1f77b4"]))
    labels = list(f5.get("labels", ["108 MHz", "179 MHz", "240 MHz"]))
    cell = float(cfg["imaging"]["cell_arcsec"])
    extent = pickle_hpc_extent(cell_arcsec=cell)

    fig, ax = plt.subplots(figsize=(6.2, 5.8))
    ax.set_facecolor("white")
    for ch, color, label in zip(channels, colors, labels):
        total_path = tbdir / f"Tb_20151203_{ch}.p"
        res_path = tbdir / f"res_20151203_{ch}.p"
        print(f"fig5  {label}  frame {frame}", file=sys.stderr)
        total = np.asarray(load_sharma_pickle(total_path)[0][frame], dtype=np.float64)
        residual = residual_tb_frame(res_path, frame)
        ax.contour(
            total,
            levels=[contour_k],
            colors=[color],
            linewidths=1.0,
            extent=extent,
            origin="lower",
        )
        masked = np.ma.masked_where(
            (residual < threshold_k) | (mask_disk & (total < contour_k)),
            residual,
        )
        cmap = LinearSegmentedColormap.from_list(f"res_{ch}", ["white", color])
        ax.imshow(
            masked,
            origin="lower",
            extent=extent,
            cmap=cmap,
            vmin=threshold_k,
            vmax=max(float(np.nanmax(residual)), threshold_k * 2),
            interpolation="nearest",
            alpha=0.85,
        )
        ax.plot([], [], color=color, lw=2, label=label)

    _limb(ax, limb)
    _style_hpc(ax, fov)
    ax.legend(loc="upper right", frameon=False, fontsize=9)
    ax.set_title("03:24:36.5–03:24:37.0 UT", fontsize=10)
    fig.tight_layout()
    dest = dest or _output_dir(cfg) / "fig5.png"
    fig.savefig(dest, dpi=160)
    plt.close(fig)
    print(f"wrote {dest}")
    return dest


_BURSTS: dict[str, BurstMaps] = {}
_TOTALS: dict[str, tuple] = {}


def _sub_extent(cfg: dict) -> list[float]:
    f7 = _figure_cfg(cfg).get("fig7", {})
    npix = int(f7.get("npix", 200))
    cell = float(f7.get("cell_arcsec", 25.0))
    return pickle_hpc_extent(npix=npix, cell_arcsec=cell, sun_in_crop=((npix - 1) / 2.0,) * 2)


def _ref_npix_beam(cfg: dict) -> float:
    tbdir = _tb_dir(cfg)
    bands = _published_bands(cfg)
    last = bands[-1]
    sub = load_sub_cube(tbdir / f"Tb_20151203_{last['channels']}_sub.p")
    cell = float(_figure_cfg(cfg).get("fig7", {}).get("cell_arcsec", 25.0))
    return pixels_per_beam(sub["bmaj_deg"], sub["bmin_deg"], cell)


def _bursts_for(cfg: dict, band: dict, ref_npix: float) -> BurstMaps:
    ch = band["channels"]
    if ch not in _BURSTS:
        f7 = _figure_cfg(cfg).get("fig7", {})
        path = _tb_dir(cfg) / f"Tb_20151203_{ch}_sub.p"
        print(f"detect {band['label']:7s}  {path.name}", file=sys.stderr)
        sub = load_sub_cube(path)
        _BURSTS[ch] = detect(
            sub["cube"],
            bmaj_deg=sub["bmaj_deg"],
            bmin_deg=sub["bmin_deg"],
            cell_arcsec=float(f7.get("cell_arcsec", 25.0)),
            nsigma_time=float(f7.get("nsigma_time", 6.0)),
            nsigma_map=float(f7.get("nsigma_map", 5.0)),
            min_pix=int(f7.get("min_pix", 3)),
            ref_npix_beam=ref_npix,
        )
        print(
            f"  frames={_BURSTS[ch].n_frames}  detections={_BURSTS[ch].n_detected}  "
            f"npix/beam={_BURSTS[ch].npix_beam:.1f}",
            file=sys.stderr,
        )
    return _BURSTS[ch]


def _total_and_contour(cfg: dict, band: dict) -> tuple[np.ndarray, float, list[float]]:
    """Time-median total T_B and 5 σ_map contour level (K)."""
    ch = band["channels"]
    if ch not in _TOTALS:
        f3 = _figure_cfg(cfg).get("fig3", {})
        path = _tb_dir(cfg) / f"Tb_20151203_{ch}.p"
        tot = time_reduce_tb(path, skip_obsids=f3.get("skip_obsids", [1133149192]))
        ny, nx = tot.shape
        cell = float(cfg["imaging"]["cell_arcsec"])
        yy, xx = np.mgrid[0:ny, 0:nx]
        r = np.hypot((xx - (nx - 1) / 2.0) * cell, (yy - (ny - 1) / 2.0) * cell)
        sigma = float(np.nanstd(tot[r > 1600]))
        level = 5.0 * sigma if sigma > 0 else 2.0e4
        extent = pickle_hpc_extent(npix=ny, cell_arcsec=cell)
        _TOTALS[ch] = (tot, level, extent)
    return _TOTALS[ch]


def _mhz_labels(cfg: dict) -> list[int]:
    return list(_figure_cfg(cfg).get("fig3", {}).get("paper_mhz", []))


def fig7(cfg: dict, dest: Path | None = None) -> Path:
    """Burst-count maps and 1σ temporal rms (paper Figure 7)."""
    fcfg = _figure_cfg(cfg)
    fov = float(fcfg.get("fov_arcsec", 2000))
    limb = float(fcfg.get("limb_arcmin", 16.0)) * 60.0
    bands = _published_bands(cfg)
    mhz = _mhz_labels(cfg)
    ref = _ref_npix_beam(cfg)
    extent = _sub_extent(cfg)

    counts, rms, totals = [], [], []
    for band in bands:
        b = _bursts_for(cfg, band, ref)
        counts.append(b.counts)
        rms.append(b.rms)
        totals.append(_total_and_contour(cfg, band))

    fig, axes = plt.subplots(4, 4, figsize=(12.4, 12.0), sharex=True, sharey=True)
    count_axes = axes[:2].ravel()
    rms_axes = axes[2:].ravel()
    last_c = last_r = None
    for i, (ax, band, nmap) in enumerate(zip(count_axes, bands, counts)):
        tot, level, cext = totals[i]
        show = np.ma.masked_less_equal(nmap, 0)
        last_c = ax.imshow(
            show,
            origin="lower",
            extent=extent,
            cmap="YlOrBr",
            norm=LogNorm(vmin=1, vmax=100),
            interpolation="nearest",
        )
        ax.contour(tot, levels=[level], colors=["#006400"], linewidths=1.0, extent=cext, origin="lower")
        _limb(ax, limb)
        _style_hpc(ax, fov)
        label = mhz[i] if i < len(mhz) else int(round(band["freq_mhz"]))
        ax.set_title(f"{label} MHz", fontsize=9, pad=3)
    for i, (ax, band, rmap) in enumerate(zip(rms_axes, bands, rms)):
        tot, level, cext = totals[i]
        last_r = ax.imshow(
            np.clip(rmap, 1, None),
            origin="lower",
            extent=extent,
            cmap="YlOrRd",
            norm=LogNorm(vmin=100, vmax=600),
            interpolation="nearest",
        )
        ax.contour(tot, levels=[level], colors=["#006400"], linewidths=1.0, extent=cext, origin="lower")
        _limb(ax, limb)
        _style_hpc(ax, fov)
        label = mhz[i] if i < len(mhz) else int(round(band["freq_mhz"]))
        ax.set_title(f"{label} MHz", fontsize=9, pad=3)
    for ax in axes[:, 1:].ravel():
        ax.set_ylabel("")
    for ax in axes[:3].ravel():
        ax.set_xlabel("")

    fig.subplots_adjust(left=0.06, right=0.88, top=0.96, bottom=0.05, wspace=0.08, hspace=0.22)
    cax1 = fig.add_axes([0.90, 0.55, 0.015, 0.38])
    cax2 = fig.add_axes([0.90, 0.07, 0.015, 0.38])
    fig.colorbar(last_c, cax=cax1, label="Number")
    fig.colorbar(last_r, cax=cax2, label=r"$T_B$ (K)")
    fig.text(0.02, 0.75, "(A)", fontsize=12, fontweight="bold")
    fig.text(0.02, 0.27, "(B)", fontsize=12, fontweight="bold")

    dest = dest or _output_dir(cfg) / "fig7.png"
    fig.savefig(dest, dpi=140)
    plt.close(fig)
    print(f"wrote {dest}")
    return dest


def _aia_file(cfg: dict) -> Path:
    euv = local_path(cfg, cfg["remote"]["paths"]["euv"])
    name = _figure_cfg(cfg).get("fig9", {}).get(
        "aia", "aia.lev1.193A_2015-12-03T03_40_29.84Z.image_lev1.fits"
    )
    return euv / name


def fig9(cfg: dict, dest: Path | None = None) -> Path:
    """AIA 193 Å + 240 MHz with the six paper regions (Figure 9)."""
    fcfg = _figure_cfg(cfg)
    f9 = fcfg.get("fig9", {})
    fov = float(f9.get("fov_arcsec", 1800))
    limb = float(fcfg.get("limb_arcmin", 16.0)) * 60.0
    bands = _published_bands(cfg)
    high = bands[-1]
    low = bands[0]
    tot240, _, ext240 = _total_and_contour(cfg, high)
    tot108, level108, ext108 = _total_and_contour(cfg, low)
    aia, aia_ext = aia_hpc_cutout(_aia_file(cfg), fov_arcsec=fov, npix=int(f9.get("aia_npix", 800)))

    fig, ax = plt.subplots(figsize=(6.4, 6.2))
    finite = aia[np.isfinite(aia) & (aia > 0)]
    vmin, vmax = np.percentile(finite, [1, 99.5]) if finite.size else (0, 1)
    ax.imshow(aia, origin="lower", extent=aia_ext, cmap="sdoaia193", vmin=vmin, vmax=vmax)
    tb = np.ma.masked_less(tot240 / 1e6, 0.05)
    ax.imshow(
        tb,
        origin="lower",
        extent=ext240,
        cmap=fcfg.get("cmap", "jet"),
        vmin=0.05,
        vmax=0.40,
        interpolation="nearest",
        alpha=0.45,
    )
    ax.contour(tot108, levels=[level108], colors=["#d62728"], linewidths=1.1, extent=ext108, origin="lower")
    _limb(ax, limb)
    radius = float(f9.get("region_radius_arcsec", 90))
    for reg in f9.get("regions", []):
        x, y = float(reg["x"]), float(reg["y"])
        ax.add_patch(Circle((x, y), radius, fill=False, color="black", lw=1.0))
        ax.text(x, y + radius + 40, str(reg["id"]), ha="center", va="bottom", fontsize=9, color="black")
    _style_hpc(ax, fov)
    ax.set_title("AIA 193 Å + 240 MHz")
    fig.tight_layout()
    dest = dest or _output_dir(cfg) / "fig9.png"
    fig.savefig(dest, dpi=160)
    plt.close(fig)
    print(f"wrote {dest}")
    return dest


_FIG11_CLIM = {
    "084-085": (-200, 200),
    "093-094": (-100, 100),
    "103-104": (-100, 100),
    "113-114": (-100, 100),
    "139-140": (-40, 40),
    "153-154": (-40, 40),
    "169-170": (-40, 40),
    "187-188": (-40, 40),
}

_FIG12_COLORS = [
    "#808000",
    "#e377c2",
    "#9467bd",
    "#d62728",
    "#2ca02c",
    "#17becf",
    "#ff7f0e",
    "#1f77b4",
]


def fig11(cfg: dict, dest: Path | None = None) -> Path:
    """Time-averaged residual T_B after dropping 6σ samples (Figure 11A)."""
    fcfg = _figure_cfg(cfg)
    fov = float(fcfg.get("fov_arcsec", 2000))
    limb = float(fcfg.get("limb_arcmin", 16.0)) * 60.0
    bands = _published_bands(cfg)
    mhz = _mhz_labels(cfg)
    ref = _ref_npix_beam(cfg)
    extent = _sub_extent(cfg)
    fig, axes = plt.subplots(2, 4, figsize=(12.4, 6.2), sharex=True, sharey=True)
    last = None
    for i, (ax, band) in enumerate(zip(axes.ravel(), bands)):
        b = _bursts_for(cfg, band, ref)
        tot, level, cext = _total_and_contour(cfg, band)
        lo, hi = _FIG11_CLIM.get(band["channels"], (-100, 100))
        last = ax.imshow(
            b.quiet_mean,
            origin="lower",
            extent=extent,
            cmap="RdBu_r",
            norm=TwoSlopeNorm(vmin=lo, vcenter=0.0, vmax=hi),
            interpolation="nearest",
        )
        ax.contour(tot, levels=[level], colors=["#006400"], linewidths=1.0, extent=cext, origin="lower")
        _limb(ax, limb)
        _style_hpc(ax, fov)
        label = mhz[i] if i < len(mhz) else int(round(band["freq_mhz"]))
        ax.set_title(f"{label} MHz", fontsize=9, pad=3)
    for ax in axes[:, 1:].ravel():
        ax.set_ylabel("")
    for ax in axes[0]:
        ax.set_xlabel("")
    fig.subplots_adjust(left=0.06, right=0.90, top=0.92, bottom=0.10, wspace=0.08, hspace=0.18)
    cax = fig.add_axes([0.92, 0.12, 0.015, 0.76])
    fig.colorbar(last, cax=cax, label=r"$T_B$ (K)")
    dest = dest or _output_dir(cfg) / "fig11.png"
    fig.savefig(dest, dpi=150)
    plt.close(fig)
    print(f"wrote {dest}")
    fig11b(cfg)
    return dest


def fig11b(cfg: dict, dest: Path | None = None) -> Path:
    """Quiet residual contours on AIA 193 Å (Figure 11B)."""
    return _euv_contours(cfg, which="quiet", dest=dest or _output_dir(cfg) / "fig11b.png", fov=1000)


def fig12(cfg: dict, dest: Path | None = None) -> Path:
    """Time-average of 6σ bursts (Figure 12A)."""
    fcfg = _figure_cfg(cfg)
    fov = float(fcfg.get("fov_fig5_arcsec", 2500))
    limb = float(fcfg.get("limb_arcmin", 16.0)) * 60.0
    bands = _published_bands(cfg)
    mhz = _mhz_labels(cfg)
    ref = _ref_npix_beam(cfg)
    extent = _sub_extent(cfg)
    fig, axes = plt.subplots(2, 4, figsize=(12.4, 6.2), sharex=True, sharey=True)
    last = None
    for i, (ax, band) in enumerate(zip(axes.ravel(), bands)):
        b = _bursts_for(cfg, band, ref)
        tot, level, cext = _total_and_contour(cfg, band)
        tb_kk = np.clip(b.burst_mean / 1e3, 1e-3, None)
        last = ax.imshow(
            tb_kk,
            origin="lower",
            extent=extent,
            cmap="YlOrRd",
            norm=LogNorm(vmin=0.5, vmax=10),
            interpolation="nearest",
        )
        ax.contour(tot, levels=[level], colors=["#006400"], linewidths=1.0, extent=cext, origin="lower")
        _limb(ax, limb)
        _style_hpc(ax, fov)
        label = mhz[i] if i < len(mhz) else int(round(band["freq_mhz"]))
        ax.set_title(f"{label} MHz", fontsize=9, pad=3)
    for ax in axes[:, 1:].ravel():
        ax.set_ylabel("")
    for ax in axes[0]:
        ax.set_xlabel("")
    fig.subplots_adjust(left=0.06, right=0.90, top=0.92, bottom=0.10, wspace=0.08, hspace=0.18)
    cax = fig.add_axes([0.92, 0.12, 0.015, 0.76])
    fig.colorbar(last, cax=cax, label=r"$T_B$ (kK)")
    dest = dest or _output_dir(cfg) / "fig12.png"
    fig.savefig(dest, dpi=150)
    plt.close(fig)
    print(f"wrote {dest}")
    fig12b(cfg)
    return dest


def fig12b(cfg: dict, dest: Path | None = None) -> Path:
    """Burst-average contours on AIA 193 Å (Figure 12B)."""
    return _euv_contours(cfg, which="burst", dest=dest or _output_dir(cfg) / "fig12b.png", fov=1500)


def _euv_contours(cfg: dict, *, which: str, dest: Path, fov: float) -> Path:
    fcfg = _figure_cfg(cfg)
    bands = _published_bands(cfg)
    mhz = _mhz_labels(cfg)
    ref = _ref_npix_beam(cfg)
    extent = _sub_extent(cfg)
    aia, aia_ext = aia_hpc_cutout(_aia_file(cfg), fov_arcsec=fov, npix=800)
    finite = aia[np.isfinite(aia) & (aia > 0)]
    vmin, vmax = np.percentile(finite, [1, 99.5]) if finite.size else (0, 1)
    fig, axes = plt.subplots(2, 4, figsize=(12.4, 6.2), sharex=True, sharey=True)
    for i, (ax, band) in enumerate(zip(axes.ravel(), bands)):
        b = _bursts_for(cfg, band, ref)
        field = b.quiet_mean if which == "quiet" else b.burst_mean
        ax.imshow(aia, origin="lower", extent=aia_ext, cmap="gray", vmin=vmin, vmax=vmax)
        peak = np.nanmax(field)
        if peak > 0:
            levels = [0.3 * peak, 0.5 * peak, 0.8 * peak]
            ax.contour(
                field,
                levels=levels,
                colors=[_FIG12_COLORS[i]],
                linewidths=1.0,
                extent=extent,
                origin="lower",
            )
        _limb(ax, float(fcfg.get("limb_arcmin", 16.0)) * 60.0)
        _style_hpc(ax, fov)
        label = mhz[i] if i < len(mhz) else int(round(band["freq_mhz"]))
        ax.set_title(f"{label} MHz", fontsize=9, pad=3)
    for ax in axes[:, 1:].ravel():
        ax.set_ylabel("")
    for ax in axes[0]:
        ax.set_xlabel("")
    fig.tight_layout()
    fig.savefig(dest, dpi=150)
    plt.close(fig)
    print(f"wrote {dest}")
    return dest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Rebuild Sharma et al. 2022 figures from staged T_B pickles."
    )
    parser.add_argument("--config", default="sharma2022")
    parser.add_argument(
        "--fig",
        choices=("3", "5", "7", "9", "11", "12", "all"),
        default="all",
        help="which paper figure to rebuild",
    )
    args = parser.parse_args(argv)
    cfg = load(args.config)
    if not DATA_DIR.joinpath(cfg["event"]["name"]).exists():
        print("staged data missing; run python -m solarburst.stage --bulk", file=sys.stderr)
        return 1
    _BURSTS.clear()
    _TOTALS.clear()
    if args.fig in ("3", "all"):
        fig3(cfg)
    if args.fig in ("5", "all"):
        fig5(cfg)
    if args.fig in ("7", "all"):
        fig7(cfg)
    if args.fig in ("9", "all"):
        fig9(cfg)
    if args.fig in ("11", "all"):
        fig11(cfg)
    if args.fig in ("12", "all"):
        fig12(cfg)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
