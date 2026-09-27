"""6σ burst detection on Sharma residual T_B cubes (paper §4.3).

For each pixel the light-curve scale ``σ`` is a MAD estimate so the bursts
themselves do not inflate the threshold. A sample is a detection when it
exceeds both 6σ (time) and 5 σ_map (off-Sun rms of that frame) and belongs
to a connected island of at least ``min_pix`` pixels. Burst *counts* are
the number of non-contiguous runs along time, then scaled by the inverse
beam area so a change in PSF across 108–240 MHz does not look like a
change in burst rate (Figure 7(A)).
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray
from scipy.ndimage import label

from solarburst.maps import pixels_per_beam


def mad_std(a: NDArray, axis: int = 0) -> NDArray:
    med = np.nanmedian(a, axis=axis, keepdims=True)
    return np.squeeze(1.4826 * np.nanmedian(np.abs(a - med), axis=axis, keepdims=True), axis=axis)


def _radius_arcsec(ny: int, nx: int, cell_arcsec: float) -> NDArray:
    yy, xx = np.mgrid[0:ny, 0:nx]
    sx = (xx - (nx - 1) / 2.0) * cell_arcsec
    sy = (yy - (ny - 1) / 2.0) * cell_arcsec
    return np.hypot(sx, sy)


def _n_runs(det: NDArray) -> NDArray:
    """Rising-edge count along time. ``det`` is ``(T, Y, X)`` bool."""
    t = det.astype(np.int8)
    pad = np.zeros((1,) + t.shape[1:], dtype=np.int8)
    return (np.diff(np.concatenate([pad, t], axis=0), axis=0) == 1).sum(axis=0)


def _filter_islands(det: NDArray, min_pix: int) -> NDArray:
    if min_pix <= 1:
        return det
    kept = np.zeros_like(det)
    for i in range(det.shape[0]):
        if not det[i].any():
            continue
        lab, n = label(det[i])
        if n == 0:
            continue
        sizes = np.bincount(lab.ravel())
        keep = np.where((sizes >= min_pix) & (np.arange(sizes.size) != 0))[0]
        if keep.size:
            kept[i] = np.isin(lab, keep)
    return kept


@dataclass
class BurstMaps:
    counts: NDArray
    rms: NDArray
    quiet_mean: NDArray
    burst_mean: NDArray
    radio_mask: NDArray
    sigma_map: float
    npix_beam: float
    n_frames: int
    n_detected: int


def detect(
    cube: NDArray,
    *,
    bmaj_deg: float,
    bmin_deg: float,
    cell_arcsec: float = 25.0,
    nsigma_time: float = 6.0,
    nsigma_map: float = 5.0,
    min_pix: int = 3,
    offsun_arcsec: float = 1800.0,
    noise_clip: float = 5.0,
    ref_npix_beam: float | None = None,
) -> BurstMaps:
    """Return count / rms / mean maps from a residual cube in Kelvin."""
    good = np.nanmax(np.abs(cube), axis=(1, 2)) > 1.0
    data = np.asarray(cube[good], dtype=np.float32)
    if data.size == 0:
        raise ValueError("residual cube has no non-zero frames")
    ny, nx = data.shape[1], data.shape[2]
    radius = _radius_arcsec(ny, nx, cell_arcsec)
    off = radius > offsun_arcsec

    def _frame_sigma(frame: NDArray) -> float:
        pix = frame[off]
        med = np.nanmedian(pix)
        return float(1.4826 * np.nanmedian(np.abs(pix - med)))

    sig_map = np.array([_frame_sigma(fr) for fr in data])
    keep = sig_map < (np.nanmedian(sig_map) * noise_clip)
    data = data[keep]
    sig_map = sig_map[keep]
    sig_pix = mad_std(data, axis=0)
    sig_pix = np.where(sig_pix < 1.0, 1.0, sig_pix)

    det = (
        (data > (nsigma_time * sig_pix)[None, :, :])
        & (data > (nsigma_map * sig_map)[:, None, None])
        & (data > 0)
    )
    det = _filter_islands(det, min_pix)
    raw = _n_runs(det).astype(np.float64)
    npix_b = pixels_per_beam(bmaj_deg, bmin_deg, cell_arcsec)
    scale = (ref_npix_beam / npix_b) if ref_npix_beam else 1.0
    counts = raw * scale

    rms = np.nanstd(data, axis=0)
    quiet = np.where(~det, data, np.nan)
    burst = np.where(det, data, np.nan)
    with np.errstate(all="ignore"):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            quiet_mean = np.nanmean(quiet, axis=0)
            burst_mean = np.nanmean(burst, axis=0)
    quiet_mean = np.where(np.isfinite(quiet_mean), quiet_mean, 0.0)
    burst_mean = np.where(np.isfinite(burst_mean), burst_mean, 0.0)

    sigma = float(np.nanmedian(sig_map))
    radio_mask = radius < 1600.0
    return BurstMaps(
        counts=counts,
        rms=rms,
        quiet_mean=quiet_mean,
        burst_mean=burst_mean,
        radio_mask=radio_mask,
        sigma_map=sigma,
        npix_beam=npix_b,
        n_frames=int(data.shape[0]),
        n_detected=int(det.sum()),
    )
