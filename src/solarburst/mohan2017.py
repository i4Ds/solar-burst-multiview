"""Mohan & Oberoi (2017, Sol Phys 292, 168) image flux scale and T_B.

Given disk-integrated ``S_odot`` (Oberoi 2017) and an uncalibrated image
``S'`` (Jy/beam, arbitrary scale),

    F(ν) = S_odot / ∯_C S' dΩ
    S    = F S'
    T_B  = S c² / (2 k ν² Ω_beam)

(Eqs. 2–4). Sharma & Oberoi (2020) take the contour C at 5σ of the
off-Sun RMS (the method paper used 6σ; the difference in F is < random
error, their Fig. 3). Ω_beam is the restoring-beam solid angle from
FITS ``BMAJ``/``BMIN``. ``scale=1`` in ``jybeam_to_tb`` is this formula.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from numpy.typing import NDArray

from solarburst.maps import beam_solid_angle_sr, jybeam_to_tb

LN2 = np.log(2.0)
RSUN_ARCSEC = 958.0


def pixel_solid_angle_sr(cdelt1_deg: float, cdelt2_deg: float) -> float:
    return abs(np.deg2rad(cdelt1_deg) * np.deg2rad(cdelt2_deg))


def beam_pixels(bmaj_deg: float, bmin_deg: float, cdelt1_deg: float, cdelt2_deg: float) -> float:
    return beam_solid_angle_sr(bmaj_deg, bmin_deg) / pixel_solid_angle_sr(cdelt1_deg, cdelt2_deg)


def integrated_flux_jy(
    data: NDArray,
    bmaj_deg: float,
    bmin_deg: float,
    cdelt1_deg: float,
    cdelt2_deg: float,
    mask: NDArray,
) -> float:
    """∯ S' dΩ inside ``mask``, with S' in Jy/beam."""
    pix = beam_pixels(bmaj_deg, bmin_deg, cdelt1_deg, cdelt2_deg)
    if pix <= 0:
        raise ValueError("beam area in pixels is not positive")
    return float(np.nansum(np.where(mask, data, 0.0))) / pix


def offsun_sigma(
    data: NDArray,
    header: Any,
    *,
    r_min_rsun: float = 2.5,
    rsun_arcsec: float = RSUN_ARCSEC,
) -> float:
    """RMS far from the Sun. ``header`` needs CDELT, CRPIX, CRVAL (deg)."""
    ny, nx = data.shape
    y, x = np.mgrid[:ny, :nx]
    # Small-angle offset from the reference pixel, in arcsec.
    dx = (x + 1 - float(header["CRPIX1"])) * float(header["CDELT1"]) * 3600.0
    dy = (y + 1 - float(header["CRPIX2"])) * float(header["CDELT2"]) * 3600.0
    r = np.hypot(dx, dy)
    off = data[r > r_min_rsun * rsun_arcsec]
    off = off[np.isfinite(off)]
    if off.size < 16:
        off = data[np.isfinite(data)]
    return float(np.nanstd(off))


def solar_mask(data: NDArray, sigma: float, nsig: float = 5.0) -> NDArray:
    return np.isfinite(data) & (data > nsig * sigma)


def f_nu(s_odot_jy: float, s_prime_jy: float) -> float:
    if s_prime_jy == 0:
        raise ValueError("integrated S' is zero")
    return float(s_odot_jy) / float(s_prime_jy)


def scale_image(
    data: NDArray,
    header: Any,
    s_odot_jy: float,
    *,
    nsig: float = 5.0,
    freq_hz: float | None = None,
) -> dict[str, Any]:
    """Apply Mohan F(ν) and return Jy/beam and T_B maps (scale=1)."""
    bmaj = float(header["BMAJ"])
    bmin = float(header["BMIN"])
    cdelt1 = float(header["CDELT1"])
    cdelt2 = float(header["CDELT2"])
    sigma = offsun_sigma(data, header)
    mask = solar_mask(data, sigma, nsig)
    s_prime = integrated_flux_jy(data, bmaj, bmin, cdelt1, cdelt2, mask)
    factor = f_nu(s_odot_jy, s_prime)
    scaled = np.asarray(data, dtype=np.float64) * factor
    if freq_hz is None:
        if "CRVAL3" in header and str(header.get("CTYPE3", "")).startswith("FREQ"):
            freq_hz = float(header["CRVAL3"])
        else:
            freq_hz = float(header["RESTFRQ"])
    tb = jybeam_to_tb(scaled, freq_hz, bmaj, bmin, scale=1.0)
    return {
        "f_nu": factor,
        "s_prime_jy": s_prime,
        "s_odot_jy": float(s_odot_jy),
        "nsig": nsig,
        "sigma_jybeam": sigma,
        "n_mask": int(mask.sum()),
        "jybeam": scaled,
        "tb_K": tb,
        "mask": mask,
        "freq_hz": freq_hz,
    }
