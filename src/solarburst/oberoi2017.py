"""Oberoi, Sharma & Rogers (2017, Sol Phys 292, 75) solar flux density.

Disk-integrated ``S_odot`` from the normalised short-baseline correlation
``r_N`` (their Eqs. 13 and 16) and ``S_odot = 2 k T_odot,P Ω_P / λ²``
(Eq. 10). Independent of antenna gains.

What this module measures from an MS
    ``r_N = |W_ij| / sqrt(W_ii W_jj)`` on the six shortest cross-correlations
    (Oberoi used Tile011/021/022/023; we use those names when present).

Sky model (Eqs. 6 and 8)
    ``T_Sky`` and ``T_b,Sky`` are beam-weighted integrals of Haslam et al.
    1982 (LAMBDA ``lambda_haslam408_nofilt.fits``, α = −2.55) at *this*
    pointing. That is the map Oberoi 2017 cites. Hardware terms ``T_Rec``,
    ``T_Pick-up`` and FEKO ``Ω_P`` stay on Table 1. The power pattern used
    for the integral is a 4×4 array-factor tile beam (same geometry as
    Oberoi §3.1), not their unpublished FEKO embedded patterns. On
    2015-12-03 the Sun is ~17° from the Galactic centre, so ``T_Sky`` is
    much higher than Oberoi's 2013-09-03 high-latitude Table 1.

Sharma & Oberoi (2020) used this ``S_odot`` and transferred it onto CASA
images with Mohan & Oberoi (2017); see ``solarburst.mohan2017``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

C_M_S = 299792458.0
K_B = 1.380649e-23
JY = 1e-26
SFU_JY = 1.0e4

# Oberoi et al. 2017, Table 1 (Tile011–Tile022, XX). Frequency in MHz.
TABLE1_MHZ = np.array(
    [103.0, 117.0, 131.0, 148.0, 167.0, 189.0, 213.0, 240.0, 272.0, 299.0]
)
TABLE1_T_SKY = np.array(
    [615.0, 438.0, 330.0, 253.0, 192.0, 152.0, 145.0, 140.0, 85.0, 53.0]
)
TABLE1_T_B_SKY = np.array(
    [3.78, 1.48, 1.01, 2.42, 1.79, 0.77, 5.12, 8.78, 3.82, 0.35]
)
TABLE1_T_REC = np.array(
    [30.0, 28.0, 26.0, 24.0, 21.0, 20.0, 21.0, 23.0, 27.0, 32.0]
)
TABLE1_T_PICK = np.array(
    [20.0, 17.0, 15.0, 13.0, 12.0, 12.0, 13.0, 18.0, 10.0, 9.0]
)
TABLE1_OMEGA_P = np.array(
    [0.380, 0.340, 0.283, 0.236, 0.220, 0.240, 0.228, 0.202, 0.150, 0.128]
)

# Paper's example tiles (90 m cables, best T_Rec). 2015 Phase I names.
OBEROI_TILES = ("Tile011", "Tile021", "Tile022", "Tile023")

# MWA tile geometry (Tingay et al. 2013). Delay lines: 435 ps, 5 bit.
DELAY_STEP_S = 435e-12
DIPOLE_SEP_M = 1.10
# ENU metres of the four Oberoi tiles, from a Phase-I metafits. Baseline
# lengths match the 2015-12-03 MS to a millimetre.
TILE_ENU_M = {
    "Tile011": np.array([-149.785, 265.814, 377.011]),
    "Tile021": np.array([-132.939, 282.611, 377.002]),
    "Tile022": np.array([-139.867, 275.498, 377.018]),
    "Tile023": np.array([-123.667, 284.854, 377.050]),
}
# Quiet scan of Sharma & Oberoi 2020 Fig. 4.
QUIET2015_TIME = "2015-12-03T03:42:04"
# Oberoi 2017 Fig. 1 pointing (2013-09-03, az=0, za=36.4°).
OBEROI2013_TIME = "2013-09-03T04:02:44"
OBEROI2013_AZ_DEG = 0.0
OBEROI2013_ZA_DEG = 36.4


def _interp(freq_mhz: float, y: NDArray) -> float:
    return float(np.interp(freq_mhz, TABLE1_MHZ, y))


def table1_terms(freq_mhz: float) -> dict[str, float]:
    """Hardware / beam terms at ``freq_mhz``, interpolated from Table 1."""
    return {
        "t_sky_K": _interp(freq_mhz, TABLE1_T_SKY),
        "t_b_sky_K": _interp(freq_mhz, TABLE1_T_B_SKY),
        "t_rec_K": _interp(freq_mhz, TABLE1_T_REC),
        "t_pickup_K": _interp(freq_mhz, TABLE1_T_PICK),
        "omega_p_sr": _interp(freq_mhz, TABLE1_OMEGA_P),
    }


def dipole_xy_m() -> tuple[NDArray, NDArray]:
    """4×4 dipole east, north (m). Index 0 is north-west, looking down."""
    east = np.empty(16)
    north = np.empty(16)
    for i in range(16):
        row = i // 4  # 0 = north
        col = i % 4  # 0 = west
        east[i] = (col - 1.5) * DIPOLE_SEP_M
        north[i] = (1.5 - row) * DIPOLE_SEP_M
    return east, north


def delays_for_pointing(az_deg: float, za_deg: float) -> NDArray:
    """Integer MWA delay steps (0–31) that steer the tile to ``az, za``."""
    az = np.deg2rad(az_deg)
    za = np.deg2rad(za_deg)
    e = np.sin(za) * np.sin(az)
    n = np.sin(za) * np.cos(az)
    x, y = dipole_xy_m()
    tau = -(e * x + n * y) / C_M_S
    rel = tau - np.min(tau)
    steps = np.rint(rel / DELAY_STEP_S)
    return np.clip(steps, 0, 31).astype(int)


def tile_power(
    az_deg: NDArray | float,
    za_deg: NDArray | float,
    freq_hz: float,
    delays: NDArray,
) -> NDArray:
    """Peak-normalised Stokes-I 4×4 array-factor beam.

    Same tile geometry as Oberoi 2017 §3.1. Not their FEKO embedded
    patterns (those files were never published). Below the horizon the
    beam is zero; ground pickup stays on Table 1 ``T_Pick-up``.
    """
    az = np.deg2rad(np.asarray(az_deg, dtype=np.float64))
    za = np.deg2rad(np.asarray(za_deg, dtype=np.float64))
    e = np.sin(za) * np.sin(az)
    n = np.sin(za) * np.cos(az)
    x, y = dipole_xy_m()
    k = 2.0 * np.pi * freq_hz / C_M_S
    geom = k * (e[..., None] * x + n[..., None] * y)
    delay_phase = 2.0 * np.pi * freq_hz * np.asarray(delays, dtype=np.float64) * DELAY_STEP_S
    af = np.exp(1j * (geom - delay_phase)).sum(axis=-1)
    elem = np.cos(za) ** 2
    power = (np.abs(af) ** 2) * np.where(za < 0.5 * np.pi, elem, 0.0)
    peak = float(np.max(power))
    if peak <= 0:
        raise RuntimeError("tile beam is identically zero")
    return power / peak


def _enu_unit(az_deg: float, za_deg: float) -> NDArray:
    az = np.deg2rad(az_deg)
    za = np.deg2rad(za_deg)
    return np.array(
        [np.sin(za) * np.sin(az), np.sin(za) * np.cos(az), np.cos(za)],
        dtype=np.float64,
    )


def uvw_wavelengths(
    b_enu_m: NDArray,
    az0_deg: float,
    za0_deg: float,
    freq_hz: float,
) -> NDArray:
    """Baseline in wavelengths. u local east, v local north, w to pointing."""
    s0 = _enu_unit(az0_deg, za0_deg)
    east = np.array([1.0, 0.0, 0.0])
    north = np.array([0.0, 1.0, 0.0])
    u_hat = np.cross(s0, north)
    nrm = float(np.linalg.norm(u_hat))
    if nrm < 1e-8:
        u_hat = np.cross(s0, east)
        nrm = float(np.linalg.norm(u_hat))
    u_hat = u_hat / nrm
    v_hat = np.cross(s0, u_hat)
    lam = C_M_S / freq_hz
    return np.array(
        [np.dot(b_enu_m, u_hat), np.dot(b_enu_m, v_hat), np.dot(b_enu_m, s0)],
        dtype=np.float64,
    ) / lam


def _altaz_grid(step_deg: float = 1.0) -> tuple[NDArray, NDArray, NDArray]:
    """Pixel-centred az, za (deg) and dΩ (sr) above the horizon."""
    za = np.arange(0.5 * step_deg, 90.0, step_deg)
    az = np.arange(0.5 * step_deg, 360.0, step_deg)
    za_g, az_g = np.meshgrid(za, az, indexing="ij")
    dza = np.deg2rad(step_deg)
    daz = np.deg2rad(step_deg)
    d_omega = np.sin(np.deg2rad(za_g)) * dza * daz
    return az_g, za_g, d_omega


def pointing_at(
    time: str,
    *,
    location=None,
    body: str = "sun",
) -> dict[str, float | NDArray]:
    """Alt-az of ``body`` and the nearest MWA delay pointing."""
    from astropy.coordinates import AltAz, EarthLocation, get_body
    from astropy.time import Time

    loc = location if location is not None else EarthLocation.of_site("MWA")
    t = Time(time)
    src = get_body(body, t, location=loc)
    altaz = src.transform_to(AltAz(obstime=t, location=loc))
    az = float(altaz.az.deg)
    alt = float(altaz.alt.deg)
    za = 90.0 - alt
    delays = delays_for_pointing(az, za)
    return {
        "time": time,
        "az_deg": az,
        "alt_deg": alt,
        "za_deg": za,
        "delays": delays,
    }


def sky_terms_haslam(
    freq_mhz: float,
    *,
    time: str = QUIET2015_TIME,
    az_deg: float | None = None,
    za_deg: float | None = None,
    delays: NDArray | None = None,
    step_deg: float = 1.0,
    haslam_path: str | None = None,
) -> dict[str, Any]:
    """Eqs. 6 and 8 at one frequency for one pointing.

    Haslam 1982 × 4×4 tile beam. The Sun is not in the map; it is added
    later as ``T_odot,P``. ``Ω_P`` here is the analytic beam solid angle;
    ``apply_sky_terms`` keeps Table 1 ``Ω_P`` for Eq. 10 unless told not to.
    """
    from astropy.coordinates import AltAz, EarthLocation, SkyCoord
    from astropy.time import Time
    import astropy.units as u

    from solarburst.haslam import HaslamMap, HASLAM_ALPHA, HASLAM_CITE, HASLAM_URL

    freq_hz = float(freq_mhz) * 1e6
    loc = EarthLocation.of_site("MWA")
    t = Time(time)
    if az_deg is None or za_deg is None:
        punt = pointing_at(time, location=loc)
        az_deg = float(punt["az_deg"])
        za_deg = float(punt["za_deg"])
        if delays is None:
            delays = np.asarray(punt["delays"])
    if delays is None:
        delays = delays_for_pointing(az_deg, za_deg)
    delays = np.asarray(delays, dtype=int)

    az_g, za_g, d_omega = _altaz_grid(step_deg)
    alt_g = 90.0 - za_g
    sky = SkyCoord(
        az=az_g * u.deg,
        alt=alt_g * u.deg,
        frame=AltAz(obstime=t, location=loc),
    )
    haslam = HaslamMap(haslam_path)
    t_sky_map = haslam.at_freq(sky, freq_hz)
    p_n = tile_power(az_g, za_g, freq_hz, delays)
    weight = p_n * d_omega
    omega_p = float(np.sum(weight))
    t_sky = float(np.sum(t_sky_map * weight) / omega_p)

    s = np.stack(
        [
            np.sin(np.deg2rad(za_g)) * np.sin(np.deg2rad(az_g)),
            np.sin(np.deg2rad(za_g)) * np.cos(np.deg2rad(az_g)),
            np.cos(np.deg2rad(za_g)),
        ],
        axis=-1,
    )
    t_b_per: dict[str, float] = {}
    for a, b in six_baselines(list(range(4))):
        n1, n2 = OBEROI_TILES[a], OBEROI_TILES[b]
        uvw = uvw_wavelengths(TILE_ENU_M[n2] - TILE_ENU_M[n1], az_deg, za_deg, freq_hz)
        s0 = _enu_unit(az_deg, za_deg)
        east = np.array([1.0, 0.0, 0.0])
        north = np.array([0.0, 1.0, 0.0])
        u_hat = np.cross(s0, north)
        nrm = float(np.linalg.norm(u_hat))
        if nrm < 1e-8:
            u_hat = np.cross(s0, east)
            nrm = float(np.linalg.norm(u_hat))
        u_hat = u_hat / nrm
        v_hat = np.cross(s0, u_hat)
        ell = np.tensordot(s, u_hat, axes=([-1], [0]))
        emm = np.tensordot(s, v_hat, axes=([-1], [0]))
        enn = np.tensordot(s, s0, axes=([-1], [0]))
        phase = 2.0 * np.pi * (uvw[0] * ell + uvw[1] * emm + uvw[2] * (enn - 1.0))
        integ = np.sum(t_sky_map * p_n * np.exp(-1j * phase) * d_omega)
        t_b_per[f"{n1}-{n2}"] = float(np.abs(integ) / omega_p)

    t_b_mean = float(np.mean(list(t_b_per.values())))
    t_b_011_022 = t_b_per["Tile011-Tile022"]
    table1 = table1_terms(freq_mhz)
    return {
        "freq_mhz": float(freq_mhz),
        "time": time,
        "az_deg": float(az_deg),
        "za_deg": float(za_deg),
        "delays": delays.tolist(),
        "step_deg": float(step_deg),
        "t_sky_K": t_sky,
        "t_b_sky_K": t_b_mean,
        "t_b_sky_K_tile011_022": t_b_011_022,
        "t_b_sky_per_baseline_K": t_b_per,
        "omega_p_sr": omega_p,
        "omega_p_sr_table1": table1["omega_p_sr"],
        "t_sky_K_table1": table1["t_sky_K"],
        "t_b_sky_K_table1": table1["t_b_sky_K"],
        "p_n_at_pointing": float(
            tile_power(np.array(az_deg), np.array(za_deg), freq_hz, delays)
        ),
        "t_sky_source": (
            f"haslam1982_nofilt α={HASLAM_ALPHA} {time} az={az_deg:.2f} "
            f"za={za_deg:.2f} 4x4 array-factor beam"
        ),
        "haslam_cite": HASLAM_CITE,
        "haslam_url": HASLAM_URL,
        "beam_note": (
            "P_N is a 4×4 array-factor tile beam, not Oberoi's unpublished "
            "FEKO embedded patterns. Ω_P from this beam is diagnostic; Eq. 10 "
            "keeps Table 1 Ω_P unless apply_sky_terms(use_table1_omega=False)."
        ),
    }


def apply_sky_terms(
    result: dict[str, Any],
    sky: dict[str, Any],
    *,
    use_table1_omega: bool = True,
) -> dict[str, Any]:
    """Recompute ``T_odot,P`` and ``S_odot`` with Haslam ``T_Sky`` / ``T_b,Sky``.

    Keeps the measured ``r_N`` and Table 1 ``T_Rec``, ``T_Pick-up``. Stores
    the old Table 1 sky numbers under ``table1_*`` so nothing is lost.
    """
    out = dict(result)
    out.setdefault("table1_t_sky_K", result.get("t_sky_K"))
    out.setdefault("table1_t_b_sky_K", result.get("t_b_sky_K"))
    out.setdefault("table1_omega_p_sr", result.get("omega_p_sr"))
    out.setdefault("table1_s_odot_sfu", result.get("s_odot_sfu"))
    out.setdefault("table1_t_odot_p_K", result.get("t_odot_p_K"))
    t_sky = float(sky["t_sky_K"])
    t_b = float(sky["t_b_sky_K"])
    omega = (
        float(out["table1_omega_p_sr"])
        if use_table1_omega
        else float(sky["omega_p_sr"])
    )
    out["t_sky_K"] = t_sky
    out["t_b_sky_K"] = t_b
    out["t_b_sky_K_used"] = t_b
    out["omega_p_sr"] = omega
    out["omega_p_sr_haslam_beam"] = float(sky["omega_p_sr"])
    out["t_sky_source"] = sky["t_sky_source"]
    out["haslam_cite"] = sky.get("haslam_cite")
    out["haslam_url"] = sky.get("haslam_url")
    out["haslam_az_deg"] = sky.get("az_deg")
    out["haslam_za_deg"] = sky.get("za_deg")
    out["haslam_delays"] = sky.get("delays")
    out["haslam_beam_note"] = sky.get("beam_note")
    r_n = float(result["r_N"])
    t_p = s_jy = None
    if np.isfinite(r_n) and 0.0 < r_n < 1.0:
        t_p = t_odot_p(r_n, t_sky, float(result["t_rec_K"]), float(result["t_pickup_K"]), t_b)
        s_jy = s_odot_jy(t_p, float(result["freq_mhz"]) * 1e6, omega)
    out["t_odot_p_K"] = t_p
    out["s_odot_jy"] = s_jy
    out["s_odot_sfu"] = None if s_jy is None else s_jy / SFU_JY
    return out


def t_odot_p(
    r_n: float,
    t_sky: float,
    t_rec: float,
    t_pickup: float,
    t_b_sky: float = 0.0,
) -> float:
    """Eq. 16: beam-weighted solar temperature (K)."""
    if not (0.0 < r_n < 1.0):
        raise ValueError(f"r_N={r_n} is outside (0, 1)")
    return (r_n * (t_sky + t_rec + t_pickup) - t_b_sky) / (1.0 - r_n)


def s_odot_jy(t_odot_p_k: float, freq_hz: float, omega_p_sr: float) -> float:
    """Eq. 10, in Jy."""
    lam = C_M_S / freq_hz
    return 2.0 * K_B * t_odot_p_k / lam**2 * omega_p_sr / JY


def s_odot_sfu(t_odot_p_k: float, freq_hz: float, omega_p_sr: float) -> float:
    return s_odot_jy(t_odot_p_k, freq_hz, omega_p_sr) / SFU_JY


def prefer_tiles(names: NDArray, flagged: NDArray) -> list[int] | None:
    """Return 0-based antenna ids for Oberoi's four tiles, or None."""
    lookup = {str(n).strip(): i for i, n in enumerate(names) if not flagged[i]}
    ids = []
    for tile in OBEROI_TILES:
        if tile in lookup:
            ids.append(lookup[tile])
            continue
        # Some MS store "Tile011" as "Tile11" or with a prefix.
        hits = [k for k in lookup if k.endswith(tile) or k.replace(" ", "") == tile]
        if not hits:
            return None
        ids.append(lookup[hits[0]])
    return ids


def shortest_tile_ids(
    pos: NDArray,
    flagged: NDArray,
    n_tiles: int = 4,
) -> list[int]:
    """Four unflagged tiles that form the shortest six baselines."""
    good = np.flatnonzero(~np.asarray(flagged, dtype=bool))
    if good.size < n_tiles:
        raise RuntimeError(f"only {good.size} unflagged antennas")
    pairs = [(a, b) for i, a in enumerate(good) for b in good[i + 1 :]]
    length = np.array([np.linalg.norm(pos[a] - pos[b]) for a, b in pairs])
    order = np.argsort(length)
    chosen: list[int] = []
    for a, b in (pairs[i] for i in order):
        for ant in (int(a), int(b)):
            if ant not in chosen:
                chosen.append(ant)
            if len(chosen) >= n_tiles:
                return chosen
    return chosen


def six_baselines(tile_ids: list[int]) -> list[tuple[int, int]]:
    ids = sorted(int(i) for i in tile_ids)
    return [(a, b) for i, a in enumerate(ids) for b in ids[i + 1 :]]


def _stokes_i(data: NDArray, npol: int) -> NDArray:
    """Complex Stokes I from XX/YY (or XX). Shape (row, chan)."""
    if npol >= 4:
        return 0.5 * (data[..., 0] + data[..., 3])
    if npol == 2:
        return 0.5 * (data[..., 0] + data[..., 1])
    return data[..., 0]


def _stokes_i_flag(flag: NDArray, npol: int) -> NDArray:
    if npol >= 4:
        return flag[..., 0] | flag[..., 3]
    if npol == 2:
        return flag[..., 0] | flag[..., 1]
    return flag[..., 0]


def measure_r_n(
    ms: str | Path,
    *,
    column: str | None = None,
    max_lambda: float = 15.0,
    t_b_sky_from_table: bool = False,
    use_flags: bool = False,
) -> dict[str, Any]:
    """Read one MS and return ``r_N``, ``S_odot``, and the terms used.

    ``column`` default: ``DATA`` (Oberoi's correlator output), else
    ``CORRECTED_DATA``. ``max_lambda`` is a report threshold; the six
    shortest baselines are always used, even if a couple exceed 10 λ at
    the top of the band.
    """
    from casacore.tables import table, taql

    ms = str(ms)
    ant = table(f"{ms}/ANTENNA", ack=False)
    names = ant.getcol("NAME")
    flagged = ant.getcol("FLAG_ROW")
    pos = ant.getcol("POSITION")
    ant.close()

    tile_ids = prefer_tiles(names, flagged)
    tile_source = "oberoi_names"
    if tile_ids is None:
        tile_ids = shortest_tile_ids(pos, flagged, 4)
        tile_source = "shortest_four"

    pairs = six_baselines(tile_ids)
    spw = table(f"{ms}/SPECTRAL_WINDOW", ack=False)
    chan_hz = np.asarray(spw.getcol("CHAN_FREQ")[0], dtype=np.float64)
    spw.close()
    freq_hz = float(np.mean(chan_hz))
    freq_mhz = freq_hz / 1e6
    lam = C_M_S / freq_hz
    lengths_m = [float(np.linalg.norm(pos[a] - pos[b])) for a, b in pairs]
    lengths_l = [l / lam for l in lengths_m]

    t = table(ms, ack=False)
    cols = t.colnames()
    if column is None:
        column = "DATA" if "DATA" in cols else "CORRECTED_DATA"
    if column not in cols:
        t.close()
        raise KeyError(f"{ms} has neither DATA nor {column}: {cols}")

    cond = " || ".join(
        [f"(ANTENNA1=={a} && ANTENNA2=={b})" for a, b in pairs]
        + [f"(ANTENNA1=={i} && ANTENNA2=={i})" for i in tile_ids]
    )
    sel = taql(f"select ANTENNA1, ANTENNA2, {column}, FLAG from $t where {cond}")
    nsel = sel.nrows()
    a1 = sel.getcol("ANTENNA1") if nsel else np.array([], dtype=int)
    a2 = sel.getcol("ANTENNA2") if nsel else np.array([], dtype=int)
    vis = sel.getcol(column) if nsel else np.zeros((0, 1, 4), dtype=np.complex64)
    flag = sel.getcol("FLAG") if nsel else np.ones((0, 1, 4), dtype=bool)
    sel.close()
    t.close()

    npol = vis.shape[-1] if vis.ndim == 3 else 1
    i_c = np.asarray(_stokes_i(vis, npol), dtype=np.complex128)
    # Imaging FLAG often kills autocorrelations; Oberoi needs W_ii. Default
    # drops only non-finite / exact-zero samples (same as solarburst.dynspec).
    i_flag = ~np.isfinite(i_c.real) | (np.abs(i_c) == 0)
    if use_flags:
        i_flag = i_flag | _stokes_i_flag(flag, npol)
    i_c[i_flag] = np.nan

    auto: dict[int, float] = {}
    n_auto = 0
    for aid in tile_ids:
        rows = (a1 == aid) & (a2 == aid)
        n_auto += int(rows.sum())
        auto[aid] = float(np.nanmean(np.abs(i_c[rows])))

    per_bl = []
    r_amp_vals = []
    r_re_vals = []
    for a, b in pairs:
        rows = (a1 == a) & (a2 == b)
        w_amp = float(np.nanmean(np.abs(i_c[rows])))
        w_re = float(np.nanmean(i_c[rows].real))
        w_ii, w_jj = auto[a], auto[b]
        denom = np.sqrt(w_ii * w_jj) if (w_ii > 0 and w_jj > 0) else float("nan")
        r_amp = w_amp / denom if np.isfinite(denom) else float("nan")
        r_re = w_re / denom if np.isfinite(denom) else float("nan")
        length_l = float(np.linalg.norm(pos[a] - pos[b]) / lam)
        if length_l <= max_lambda:
            r_amp_vals.append(r_amp)
            r_re_vals.append(r_re)
        per_bl.append(
            {
                "antenna1": int(a),
                "antenna2": int(b),
                "name1": str(names[a]).strip(),
                "name2": str(names[b]).strip(),
                "length_m": float(np.linalg.norm(pos[a] - pos[b])),
                "length_lambda": length_l,
                "n_rows": int(rows.sum()),
                "W_ij_amp": w_amp,
                "W_ij_re": w_re,
                "W_ii": w_ii,
                "W_jj": w_jj,
                "r_N_amp": r_amp,
                "r_N_re": r_re,
            }
        )

    r_n = float(np.nanmean(r_amp_vals)) if r_amp_vals else float("nan")
    terms = table1_terms(freq_mhz)
    t_b = terms["t_b_sky_K"] if t_b_sky_from_table else 0.0
    t_p = s_jy = None
    note = []
    if n_auto == 0:
        note.append("no autocorrelation rows for the chosen tiles; r_N needs W_ii (Oberoi Eq. 13)")
    if not r_amp_vals:
        note.append(f"no baselines ≤ {max_lambda} λ")
    if np.isfinite(r_n) and 0.0 < r_n < 1.0:
        t_p = t_odot_p(
            r_n, terms["t_sky_K"], terms["t_rec_K"], terms["t_pickup_K"], t_b
        )
        s_jy = s_odot_jy(t_p, freq_hz, terms["omega_p_sr"])
    elif np.isfinite(r_n):
        note.append(f"r_N={r_n} outside (0,1); S_odot not computed")
    n_over = int(sum(l > max_lambda for l in lengths_l))
    return {
        "ms": ms,
        "column": column,
        "freq_mhz": freq_mhz,
        "tile_source": tile_source,
        "tiles": [str(names[i]).strip() for i in tile_ids],
        "n_selected_rows": int(nsel),
        "n_auto_rows": n_auto,
        "r_N": r_n,
        "r_N_estimator": "mean_|V_ij|/sqrt(|V_ii||V_jj|) on baselines ≤ max_lambda",
        "r_N_amp_short": r_amp_vals,
        "r_N_re_short": r_re_vals,
        "t_odot_p_K": t_p,
        "s_odot_jy": s_jy,
        "s_odot_sfu": None if s_jy is None else s_jy / SFU_JY,
        "t_sky_source": "oberoi2017_table1_2013_pointing",
        "t_b_sky_K_used": t_b,
        "n_baselines_above_max_lambda": n_over,
        "max_lambda": max_lambda,
        "note": note,
        **terms,
        "baselines": per_bl,
    }


def write_json(result: dict[str, Any], path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2) + "\n")


def _check_table1_103mhz() -> None:
    """Eq. 10/16 against Oberoi 2017 Table 1 at 103 MHz (Tile011–022)."""
    r_n, t_sky, t_rec, t_pick, t_b = 0.174, 615.0, 30.0, 20.0, 3.78
    t_p = t_odot_p(r_n, t_sky, t_rec, t_pick, t_b)
    sfu = s_odot_sfu(t_p, 103e6, 0.380)
    # Table 1: T_odot,P = 139 K, S_odot = 1.73 SFU (100 s mean; we use the row r_N).
    if not (130.0 < t_p < 145.0):
        raise AssertionError(f"T_odot,P={t_p:.1f} K not near Table 1 139 K")
    if not (1.6 < sfu < 1.9):
        raise AssertionError(f"S_odot={sfu:.2f} SFU not near Table 1 1.73 SFU")


if __name__ == "__main__":
    _check_table1_103mhz()
    print("table1_103mhz_ok")

