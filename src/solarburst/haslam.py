"""Haslam et al. (1982, A&AS 47, 1) 408 MHz all-sky map.

The file on disk is LAMBDA ``lambda_haslam408_nofilt.fits``: the MPIfR
Survey Sampler map interpolated to HEALPix NSIDE=512, Galactic, nested,
with **no** destripe and **no** source subtraction. That is the survey
Oberoi, Sharma & Rogers (2017) cite and scale with ``α = −2.55``. It is
not Remazeilles et al. (2015).

The FITS stores millikelvin. Everything here returns kelvin.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import numpy as np
from astropy.coordinates import Galactic, SkyCoord
from astropy.io import fits
from astropy_healpix import HEALPix
from numpy.typing import NDArray

from solarburst.config import DATA_DIR

HASLAM_CITE = "Haslam et al. 1982, A&AS 47, 1"
HASLAM_FILENAME = "lambda_haslam408_nofilt.fits"
HASLAM_URL = (
    "https://lambda.gsfc.nasa.gov/data/foregrounds/haslam/lambda_haslam408_nofilt.fits"
)
# LAMBDA Content-Length on 2012-04-03 / last-modified 2012-04-04.
HASLAM_BYTES = 25_174_080
HASLAM_NU_HZ = 408.0e6
HASLAM_ALPHA = -2.55  # T ∝ ν^α; Oberoi 2017 §3.3

# Default cache. data/ is gitignored.
HASLAM_PATH = DATA_DIR / "haslam" / HASLAM_FILENAME


def haslam_path(path: str | Path | None = None) -> Path:
    return Path(path) if path is not None else HASLAM_PATH


def download_haslam(path: str | Path | None = None, *, timeout: int = 120) -> Path:
    """Fetch the unfiltered Haslam 1982 map if it is not already on disk."""
    import urllib.request

    dest = haslam_path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size == HASLAM_BYTES:
        return dest
    req = urllib.request.Request(
        HASLAM_URL,
        headers={"User-Agent": "solarburst/haslam (Haslam 1982; Oberoi 2017 flux)"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp, dest.open("wb") as fh:
        while True:
            chunk = resp.read(1 << 20)
            if not chunk:
                break
            fh.write(chunk)
    n = dest.stat().st_size
    if n != HASLAM_BYTES:
        raise RuntimeError(
            f"{dest} is {n} bytes, expected {HASLAM_BYTES} from LAMBDA {HASLAM_URL}"
        )
    return dest


def sha256(path: str | Path | None = None) -> str:
    p = haslam_path(path)
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class HaslamMap:
    """In-memory Haslam 1982 map in kelvin at 408 MHz."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = haslam_path(path)
        if not self.path.exists():
            raise FileNotFoundError(
                f"{self.path} is missing. Run solarburst.haslam.download_haslam() "
                f"or: curl -L -o {self.path} {HASLAM_URL}"
            )
        with fits.open(self.path) as hdul:
            hdu = hdul[1]
            hdr = hdu.header
            if hdr.get("PIXTYPE", "").strip().upper() != "HEALPIX":
                raise ValueError(f"{self.path} is not a HEALPix table")
            nside = int(hdr["NSIDE"])
            order = str(hdr["ORDERING"]).strip().lower()
            unit = str(hdr.get("TUNIT1", "mK")).strip().lower()
            temp = np.asarray(hdu.data["TEMPERATURE"], dtype=np.float64)
        if unit in {"mk", "millikelvin"}:
            temp = temp / 1000.0
        elif unit not in {"k", "kelvin"}:
            raise ValueError(f"unexpected Haslam unit {unit!r}")
        self.nside = nside
        self.order = order
        self.temperature_k = temp
        self.hp = HEALPix(nside=nside, order=order, frame=Galactic())
        self.header_unit = unit
        self.cite = HASLAM_CITE
        self.url = HASLAM_URL

    def at_408(self, coord: SkyCoord) -> NDArray:
        gal = coord.transform_to(Galactic())
        return np.asarray(
            self.hp.interpolate_bilinear_skycoord(gal, self.temperature_k),
            dtype=np.float64,
        )

    def at_freq(self, coord: SkyCoord, freq_hz: float) -> NDArray:
        scale = (float(freq_hz) / HASLAM_NU_HZ) ** HASLAM_ALPHA
        return self.at_408(coord) * scale

    def info(self) -> dict[str, Any]:
        return {
            "path": str(self.path),
            "url": HASLAM_URL,
            "cite": HASLAM_CITE,
            "nside": self.nside,
            "order": self.order,
            "npix": int(self.hp.npix),
            "unit_loaded": "K",
            "fits_unit": self.header_unit,
            "t408_K_min": float(np.min(self.temperature_k)),
            "t408_K_max": float(np.max(self.temperature_k)),
            "t408_K_median": float(np.median(self.temperature_k)),
            "alpha": HASLAM_ALPHA,
            "sha256": sha256(self.path) if self.path.exists() else None,
        }


def load(path: str | Path | None = None) -> HaslamMap:
    return HaslamMap(path)
