"""Jy/beam → brightness temperature and helioprojective frames.

Sharma et al. 2022 cite Mohan & Oberoi (2017) for the conversion

    T_B = S λ² / (2 k Ω_beam)

with Ω_beam the Gaussian synthesized-beam solid angle. Using the CASA FITS
``BMAJ``/``BMIN`` (degrees) that formula undershoots Sharma's published
(and pickled) T_B by a nearly frequency-independent factor of ~9.5. The
pickles in ``Tb_new/`` already have the published scale; FITS input needs
``imaging.tb_scale`` (default 9.48, measured at 108 MHz against those
pickles) to match Figure 3 peaks.

Helioprojective coordinates are a small-angle offset from the apparent
solar RA/Dec at ``DATE-OBS``. Full ``sunpy`` reprojection of these SIN
images fails because the CASA WCS has no distance; the plane-of-sky
offset is what the paper plots.
"""

from __future__ import annotations

import pickle
import warnings
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np
from astropy.coordinates import SkyCoord, get_body
from astropy.io import fits
from astropy.time import Time
from astropy.wcs import WCS
from astropy import constants as const
from numpy.typing import NDArray

LN2 = np.log(2.0)


def beam_solid_angle_sr(bmaj_deg: float, bmin_deg: float) -> float:
    """Solid angle of a 2-D Gaussian beam, ``π θ_maj θ_min / (4 ln 2)``."""
    return np.pi * np.deg2rad(bmaj_deg) * np.deg2rad(bmin_deg) / (4.0 * LN2)


def jybeam_to_tb(
    data: NDArray,
    freq_hz: float,
    bmaj_deg: float,
    bmin_deg: float,
    *,
    scale: float = 1.0,
) -> NDArray:
    """Convert Jy/beam to brightness temperature in Kelvin.

    ``scale=1`` is the Rayleigh–Jeans / Mohan & Oberoi formula with the
    given beam. Sharma's pickles match ``scale≈9.48`` at 108 MHz.
    """
    omega = beam_solid_angle_sr(bmaj_deg, bmin_deg)
    factor = scale * 1e-26 * const.c.value**2 / (
        2.0 * const.k_B.value * freq_hz**2 * omega
    )
    return np.asarray(data, dtype=np.float64) * factor


def load_casa_2d(path: Path | str) -> tuple[NDArray, fits.Header]:
    """Return the squeezed Stokes-I image and its FITS header."""
    with fits.open(path) as hdul:
        data = np.squeeze(hdul[0].data).astype(np.float64)
        header = hdul[0].header.copy()
    if data.ndim != 2:
        raise ValueError(f"{path} squeezed to {data.shape}, expected 2-D")
    return data, header


def frequency_hz(header: fits.Header) -> float:
    if "CRVAL3" in header and header.get("CTYPE3", "").startswith("FREQ"):
        return float(header["CRVAL3"])
    if "RESTFRQ" in header:
        return float(header["RESTFRQ"])
    raise KeyError("no frequency in FITS header")


def solar_pixel(header: fits.Header) -> tuple[float, float]:
    """0-indexed (x, y) pixel of the apparent Sun.

    ``get_body`` returns a GCRS coordinate with a distance; the CASA SIN
    WCS cannot transform that, so we pass RA/Dec only.
    """
    wcs = WCS(header).celestial
    sun = get_body("sun", Time(header["DATE-OBS"]))
    x, y = wcs.world_to_pixel(SkyCoord(ra=sun.ra, dec=sun.dec))
    return float(x), float(y)


def crop_around_sun(
    data: NDArray,
    header: fits.Header,
    npix: int = 100,
) -> tuple[NDArray, tuple[int, int], tuple[float, float]]:
    """Square crop centred on the Sun. Returns crop, (x0, y0), sun pixel."""
    sx, sy = solar_pixel(header)
    x0 = int(round(sx - (npix - 1) / 2.0))
    y0 = int(round(sy - (npix - 1) / 2.0))
    crop = data[y0 : y0 + npix, x0 : x0 + npix]
    if crop.shape != (npix, npix):
        raise ValueError(
            f"sun-centred crop {crop.shape} at origin ({x0}, {y0}); "
            f"image is {data.shape}"
        )
    return crop, (x0, y0), (sx, sy)


def hpc_extent(
    ny: int,
    nx: int,
    *,
    cell_arcsec: float,
    sun_xy: tuple[float, float],
    origin: tuple[int, int] = (0, 0),
) -> list[float]:
    """``imshow`` extent in helioprojective arcsec for ``origin='lower'``.

    ``sun_xy`` is the Sun's pixel in the *parent* array; ``origin`` is the
    crop's ``(x0, y0)``. Increasing column (CDELT1 < 0) is +Solar X.
    """
    sx, sy = sun_xy
    x0, y0 = origin
    cx = sx - x0
    cy = sy - y0
    cell = float(cell_arcsec)
    return [
        (0.0 - 0.5 - cx) * cell,
        (nx - 0.5 - cx) * cell,
        (0.0 - 0.5 - cy) * cell,
        (ny - 0.5 - cy) * cell,
    ]


def header_cell_arcsec(header: fits.Header) -> float:
    return abs(float(header["CDELT2"])) * 3600.0


def fits_to_tb_hpc(
    path: Path | str,
    *,
    scale: float = 1.0,
    npix: int = 100,
    bmaj_deg: float | None = None,
    bmin_deg: float | None = None,
) -> tuple[NDArray, list[float], fits.Header]:
    """Load a CASA image, convert to T_B (K), crop around the Sun.

    Residual FITS often omit ``BMAJ``; pass the matching ``*.image.FITS``
    beam in that case.
    """
    data, header = load_casa_2d(path)
    bmaj = bmaj_deg if bmaj_deg is not None else float(header["BMAJ"])
    bmin = bmin_deg if bmin_deg is not None else float(header["BMIN"])
    tb = jybeam_to_tb(data, frequency_hz(header), bmaj, bmin, scale=scale)
    crop, origin, sun_xy = crop_around_sun(tb, header, npix=npix)
    extent = hpc_extent(
        crop.shape[0],
        crop.shape[1],
        cell_arcsec=header_cell_arcsec(header),
        sun_xy=sun_xy,
        origin=origin,
    )
    return crop, extent, header


def load_sharma_pickle(path: Path | str) -> list[Any]:
    """Load a numpy-1.x pickle written on Rohit's machine."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        with open(path, "rb") as fh:
            return pickle.load(fh, encoding="latin1")


def _obsid_in_path(path: str, obsids: Sequence[str | int]) -> bool:
    text = str(path)
    return any(str(o) in text for o in obsids)


def time_reduce_tb(
    pickle_path: Path | str,
    *,
    skip_obsids: Iterable[str | int] = (),
    how: str = "median",
    shape: tuple[int, int] = (100, 100),
) -> NDArray:
    """Time-median (or mean) of Sharma ``Tb_*.p`` maps, in Kelvin.

    Frames that are not ``shape``, not arrays, or whose source FITS path
    contains a skipped obsid are dropped. ``median`` is the robust choice:
    a handful of 197/240 MHz frames are hundreds of MK and wreck a mean.
    """
    obj = load_sharma_pickle(pickle_path)
    skip = tuple(skip_obsids)
    frames: list[NDArray] = []
    files = obj[11] if len(obj) > 11 else [""] * len(obj[0])
    for arr, src in zip(obj[0], files):
        if not isinstance(arr, np.ndarray) or tuple(arr.shape) != shape:
            continue
        if skip and _obsid_in_path(str(src), skip):
            continue
        frames.append(np.asarray(arr, dtype=np.float32))
    if not frames:
        raise ValueError(f"no {shape} frames in {pickle_path}")
    stack = np.stack(frames)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        if how == "median":
            reduced = np.nanmedian(stack, axis=0)
        elif how == "mean":
            reduced = np.nanmean(stack, axis=0)
        else:
            raise ValueError(f"unknown reduce {how!r}")
    return np.asarray(reduced, dtype=np.float64)


def pickle_hpc_extent(
    npix: int = 100,
    cell_arcsec: float = 50.0,
    sun_in_crop: tuple[float, float] = (49.5, 49.5),
) -> list[float]:
    """HPC extent for a Sharma 100×100 pickle crop (sun near pixel 50, 50)."""
    return hpc_extent(
        npix,
        npix,
        cell_arcsec=cell_arcsec,
        sun_xy=sun_in_crop,
        origin=(0, 0),
    )


def residual_tb_frame(pickle_path: Path | str, index: int = 0) -> NDArray:
    """Return one frame of ``res_*.p`` brightness temperature (K).

    Layout: ``[0]`` Jy/beam residual crops, ``[1]`` T_B residual crops.
    """
    obj = load_sharma_pickle(pickle_path)
    frame = obj[1][index]
    if not isinstance(frame, np.ndarray):
        raise TypeError(f"{pickle_path} residual frame {index} is {type(frame)}")
    return np.asarray(frame, dtype=np.float64)


def load_sub_cube(path: Path | str) -> dict[str, Any]:
    """Load a ``Tb_*_sub.p`` residual cube.

    ``[0]`` is ``(time, y, x)`` T_B in K at 1 s, 200², 25″ pixels.
    ``[4]`` are time strings, ``[6]``/``[7]``/``[8]`` are BMAJ/BMIN (deg) and BPA.
    """
    obj = load_sharma_pickle(path)
    cube = np.asarray(obj[0], dtype=np.float32)
    return {
        "cube": cube,
        "times": list(obj[4]),
        "bmaj_deg": float(obj[6]),
        "bmin_deg": float(obj[7]),
        "bpa_deg": float(obj[8]),
        "rsun_arcsec": float(np.median(obj[2])),
    }


def pixels_per_beam(bmaj_deg: float, bmin_deg: float, cell_arcsec: float) -> float:
    """Gaussian beam area in pixels, ``Ω_beam / Ω_pix``."""
    omega = beam_solid_angle_sr(bmaj_deg, bmin_deg)
    pix = (cell_arcsec / 3600.0 * np.pi / 180.0) ** 2
    return float(omega / pix)


def aia_hpc_cutout(
    path: Path | str,
    *,
    fov_arcsec: float = 2000.0,
    npix: int = 800,
) -> tuple[NDArray, list[float]]:
    """Cut an AIA 193 Å level-1 image to a square HPC box.

    ``npix`` is unused (AIA keeps its native 0.6″ pixels); it is kept so
    callers can stay stable if we resample later.
    """
    import astropy.units as u
    from astropy.coordinates import SkyCoord
    from sunpy.map import Map

    del npix  # native AIA resolution is finer than we plot
    smap = Map(str(path))
    fov = float(fov_arcsec) * u.arcsec
    bottom_left = SkyCoord(-fov, -fov, frame=smap.coordinate_frame)
    top_right = SkyCoord(fov, fov, frame=smap.coordinate_frame)
    cut = smap.submap(bottom_left, top_right=top_right)
    bl = cut.bottom_left_coord
    tr = cut.top_right_coord
    extent = [
        float(bl.Tx.to_value(u.arcsec)),
        float(tr.Tx.to_value(u.arcsec)),
        float(bl.Ty.to_value(u.arcsec)),
        float(tr.Ty.to_value(u.arcsec)),
    ]
    return np.asarray(cut.data, dtype=np.float64), extent
