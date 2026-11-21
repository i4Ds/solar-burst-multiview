"""Sharma & Oberoi 2020 Fig. 4: T_B from Rohit's 0.5 s CASA images.

Section 4 of the paper: convert each 0.5 s map to T_B with Mohan & Oberoi
(2017) at 5σ, then take the time mean. This module does that, on the FITS
that CASA 5.3 already wrote (HISTORY: SuperUniform, Hogbom, niter 8000).

It does not re-image. Re-imaging is ``scripts/calculon/sharma2020_casa_snap.py``.
It does not use ``imaging.tb_scale``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from astropy.io import fits
from solarburst.maps import (
    frequency_hz,
    header_cell_arcsec,
    hpc_extent,
    load_casa_2d,
    solar_pixel,
)
from solarburst.mohan2017 import scale_image

OBSID = "1133149192"
BANDS = (
    ("108", "084-085", 0.92),
    ("162", "125-126", 1.20),
    ("217", "169-170", 1.50),
    ("240", "187-188", None),
)
NPIX = 100
NSIG = 5.0

# Last clean() that wrote the published FITS (CASA 5.3.0-143, May 2020).
CLEAN = {
    "task": "clean",
    "imsize": [1024, 1024],
    "cell": "50arcsec",
    "stokes": "I",
    "mode": "mfs",
    "weighting": "superuniform",
    "npixels": 0,
    "psfmode": "hogbom",
    "imagermode": "",
    "niter": 8000,
    "gain": 0.1,
    "threshold": "0mJy",
    "uvrange": "",
    "phasecenter": "J2000 16h40m55.28s -19d40m25.38s",
}


def list_fits(fitsdir: Path, channels: str) -> list[Path]:
    stem = f"{OBSID}-{channels}"
    paths = sorted(fitsdir.glob(f"{stem}.*.image_image.FITS"))
    if not paths:
        paths = sorted(fitsdir.glob(f"{stem}.*.image.FITS"))
    if not paths:
        raise FileNotFoundError(f"no FITS for {stem} in {fitsdir}")
    return paths


def last_clean_from_history(path: Path | str) -> dict[str, str]:
    """Parse the last ``imager::clean()`` block in a CASA FITS HISTORY."""
    header = fits.getheader(path)
    lines = [str(x).replace("\n", " ") for x in header["HISTORY"]]
    out: dict[str, str] = {
        "origin": str(header.get("ORIGIN", "")),
        "bmaj_arcsec": f"{float(header['BMAJ']) * 3600:.1f}",
        "bmin_arcsec": f"{float(header['BMIN']) * 3600:.1f}",
    }
    for line in reversed(lines):
        if "Clean gain" in line and "niter" not in out:
            out["niter"] = line.split("MESSAGE:", 1)[-1].strip()
        if "SuperUniform" in line and "weighting" not in out:
            out["weighting"] = line.split("MESSAGE:", 1)[-1].strip()
        if "Briggs weighting" in line and "weighting" not in out:
            out["weighting"] = line.split("MESSAGE:", 1)[-1].strip()
        if "Hogbom" in line and "deconvolver" not in out:
            out["deconvolver"] = line.split("MESSAGE:", 1)[-1].strip() if "MESSAGE:" in line else line
        if "Fitted beam" in line and "fitted_beam" not in out:
            out["fitted_beam"] = line.split("MESSAGE:", 1)[-1].strip()
        if len(out) >= 7:
            break
    return out


def _crop_header(hdr0: fits.Header, npix: int) -> fits.Header:
    hdr = hdr0.copy()
    hdr["CRPIX1"] = (npix + 1) / 2.0
    hdr["CRPIX2"] = (npix + 1) / 2.0
    return hdr


def mean_tb_per_frame(
    fitsdir: Path,
    channels: str,
    s_odot_jy: float,
    *,
    nsig: float = NSIG,
    npix: int = NPIX,
) -> dict[str, Any]:
    """Time-mean T_B of the 0.5 s maps, F(ν) applied per frame (paper §4)."""
    paths = list_fits(fitsdir, channels)
    data0, hdr0 = load_casa_2d(paths[0])
    sun_xy = solar_pixel(hdr0)
    x0 = int(round(sun_xy[0] - (npix - 1) / 2.0))
    y0 = int(round(sun_xy[1] - (npix - 1) / 2.0))
    extent = hpc_extent(
        npix, npix, cell_arcsec=header_cell_arcsec(hdr0), sun_xy=sun_xy, origin=(x0, y0)
    )
    acc = np.zeros((npix, npix), dtype=np.float64)
    f_nu: list[float] = []
    beams: list[tuple[float, float, float]] = []
    freq = frequency_hz(hdr0)
    for i, path in enumerate(paths):
        data, hdr = load_casa_2d(path)
        crop = data[y0 : y0 + npix, x0 : x0 + npix]
        hdr_c = _crop_header(hdr, npix)
        rec = scale_image(crop, hdr_c, s_odot_jy, nsig=nsig, freq_hz=frequency_hz(hdr))
        acc += rec["tb_K"]
        f_nu.append(float(rec["f_nu"]))
        beams.append((float(hdr["BMAJ"]), float(hdr["BMIN"]), float(hdr.get("BPA", 0.0))))
        if (i + 1) % 100 == 0 or i + 1 == len(paths):
            print(f"  {channels}  {i + 1}/{len(paths)}  F(ν)={f_nu[-1]:.2f}", flush=True)
    mean = acc / len(paths)
    bmaj, bmin, bpa = np.median(np.asarray(beams), axis=0)
    f = np.asarray(f_nu, dtype=np.float64)
    return {
        "tb": mean.astype(np.float32),
        "extent": np.asarray(extent, dtype=np.float64),
        "bmaj_deg": float(bmaj),
        "bmin_deg": float(bmin),
        "bpa_deg": float(bpa),
        "n": len(paths),
        "freq_hz": float(freq),
        "f_nu": f,
        "f_nu_mean": float(np.mean(f)),
        "f_nu_std": float(np.std(f)),
        "s_odot_jy": float(s_odot_jy),
        "nsig": float(nsig),
    }
