"""Visibility-domain background subtraction.

The Sharma et al. 2022 paper (ApJ 937, 99, §4.1) describes a 15 s running
median of Re/Im per baseline. The CASA logs for the validation pair show
something simpler: `subvs` in `mode="linear"` averaged **all** visibilities
in `subtime1` (the whole 5-minute scan, including flagged samples) and
subtracted that complex constant. `scan_mean` reproduces that; it is what
the Phase 1 gate checks. `running_median` is the published method.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from solarburst.config import load, local_path
from solarburst.stage import open_ms

ComplexArray = NDArray[np.complexfloating]


def _baseline_index(antenna1: NDArray, antenna2: NDArray) -> tuple[NDArray, NDArray]:
    key = antenna1.astype(np.int64) * 65536 + antenna2.astype(np.int64)
    _, inverse = np.unique(key, return_inverse=True)
    return key, inverse


def scan_mean(
    data: ComplexArray,
    antenna1: NDArray,
    antenna2: NDArray,
    *,
    flag: NDArray | None = None,
    include_flagged: bool = True,
) -> ComplexArray:
    """Subtract the per-baseline, per-channel, per-pol time mean.

    This is CASA `subvs` with `mode="linear"` and a single `subtime1` covering
    the whole scan. Flagged samples are included in the mean when
    `include_flagged` is true, which is what produced `chan_sub.ms`.
    """
    _, inverse = _baseline_index(antenna1, antenna2)
    nbl = int(inverse.max()) + 1
    nchan, npol = data.shape[1], data.shape[2]
    d = np.asarray(data, dtype=np.complex128)
    if include_flagged or flag is None:
        mask = np.ones(d.shape, dtype=bool)
    else:
        mask = ~np.asarray(flag, dtype=bool)

    sums = np.zeros((nbl, nchan, npol), dtype=np.complex128)
    counts = np.zeros((nbl, nchan, npol), dtype=np.int64)
    for c in range(nchan):
        for p in range(npol):
            m = mask[:, c, p]
            np.add.at(sums[:, c, p].real, inverse[m], d[m, c, p].real)
            np.add.at(sums[:, c, p].imag, inverse[m], d[m, c, p].imag)
            np.add.at(counts[:, c, p], inverse[m], 1)
    means = np.zeros_like(sums)
    good = counts > 0
    means[good] = sums[good] / counts[good]
    return (d - means[inverse]).astype(data.dtype, copy=False)


def running_median(
    data: ComplexArray,
    antenna1: NDArray,
    antenna2: NDArray,
    time: NDArray,
    *,
    window_s: float = 15.0,
    clip_sigma: float | None = 5.0,
    flag: NDArray | None = None,
) -> ComplexArray:
    """Subtract a running median of Re and Im independently (paper §4.1).

    `window_s` is the full window width in seconds. Outliers beyond
    `clip_sigma` (MAD-scaled) are ignored inside each baseline light curve
    before the median is taken, matching the paper's 5σ clip.
    """
    from scipy.ndimage import median_filter

    _, inverse = _baseline_index(antenna1, antenna2)
    nbl = int(inverse.max()) + 1
    d = np.asarray(data, dtype=np.complex128).copy()
    nchan, npol = d.shape[1], d.shape[2]
    flagged = np.zeros(d.shape, dtype=bool) if flag is None else np.asarray(flag, dtype=bool)

    cadence = float(np.median(np.diff(np.unique(time))))
    width = max(1, int(round(window_s / cadence)))
    if width % 2 == 0:
        width += 1

    out = np.empty_like(d)
    for bl in range(nbl):
        rows = np.flatnonzero(inverse == bl)
        order = np.argsort(time[rows], kind="mergesort")
        idx = rows[order]
        sl = d[idx]
        fl = flagged[idx]
        for c in range(nchan):
            for p in range(npol):
                re = sl[:, c, p].real.copy()
                im = sl[:, c, p].imag.copy()
                bad = fl[:, c, p]
                if clip_sigma is not None:
                    for arr in (re, im):
                        finite = arr[~bad] if bad.any() else arr
                        if finite.size < 3:
                            continue
                        med0 = np.median(finite)
                        mad = np.median(np.abs(finite - med0))
                        sigma = 1.4826 * mad if mad > 0 else np.std(finite)
                        if sigma > 0:
                            bad = bad | (np.abs(arr - med0) > clip_sigma * sigma)
                re_m = re.copy()
                im_m = im.copy()
                re_m[bad] = np.nan
                im_m[bad] = np.nan
                # median_filter cannot nan; fill with local median of valid
                fill_re = np.nanmedian(re_m)
                fill_im = np.nanmedian(im_m)
                if not np.isfinite(fill_re):
                    fill_re = 0.0
                if not np.isfinite(fill_im):
                    fill_im = 0.0
                re_f = np.where(np.isfinite(re_m), re_m, fill_re)
                im_f = np.where(np.isfinite(im_m), im_m, fill_im)
                bg_re = median_filter(re_f, size=width, mode="nearest")
                bg_im = median_filter(im_f, size=width, mode="nearest")
                sl[:, c, p] = (re - bg_re) + 1j * (im - bg_im)
        out[idx] = sl
    return out.astype(data.dtype, copy=False)


def subtract_ms(
    vis: Path | str,
    *,
    method: str = "scan_mean",
    window_s: float = 15.0,
    clip_sigma: float | None = 5.0,
    include_flagged: bool = True,
) -> np.ndarray:
    """Return residual DATA for `vis` without writing a new MS."""
    t = open_ms(vis)
    try:
        data = t.getcol("DATA")
        a1 = t.getcol("ANTENNA1")
        a2 = t.getcol("ANTENNA2")
        flag = t.getcol("FLAG")
        if method == "scan_mean":
            return scan_mean(
                data, a1, a2, flag=flag, include_flagged=include_flagged
            )
        if method == "running_median":
            time = t.getcol("TIME")
            return running_median(
                data,
                a1,
                a2,
                time,
                window_s=window_s,
                clip_sigma=clip_sigma,
                flag=flag,
            )
        raise ValueError(f"unknown subtraction method {method!r}")
    finally:
        t.close()


def write_ms(src: Path | str, dest: Path | str, data: np.ndarray) -> Path:
    """Copy `src` to `dest` and replace DATA. Overwrites `dest` if present."""
    src = Path(src)
    dest = Path(dest)
    if dest.exists():
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    from casacore.tables import table, tablecopy

    tablecopy(str(src), str(dest))
    t = table(str(dest), readonly=False)
    try:
        t.putcol("DATA", np.asarray(data, dtype=t.getcell("DATA", 0).dtype))
    finally:
        t.close()
    return dest


def compare(ours: np.ndarray, expected: np.ndarray, flag: np.ndarray | None = None) -> dict:
    """Absolute residual between two DATA columns."""
    d = np.abs(np.asarray(ours) - np.asarray(expected))
    unflagged = d if flag is None else np.where(flag, np.nan, d)
    return {
        "max": float(np.nanmax(unflagged)),
        "median": float(np.nanmedian(unflagged)),
        "mean": float(np.nanmean(unflagged)),
        "all_max": float(np.max(d)),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Subtract slowly-varying visibilities; compare to Sharma's _sub.ms."
    )
    parser.add_argument("--config", default="sharma2022")
    parser.add_argument(
        "--method",
        choices=("scan_mean", "running_median"),
        default=None,
        help="override config (default: validation.subtraction.method or scan_mean)",
    )
    parser.add_argument(
        "--write",
        nargs="?",
        const="auto",
        default=None,
        help="write residual MS; omit path to use <input>_ours.ms",
    )
    args = parser.parse_args(argv)

    cfg = load(args.config)
    spec = cfg["validation"]["subtraction"]
    method = args.method or spec.get("method", "scan_mean")
    include_flagged = spec.get("include_flagged", True)
    window_s = float(spec.get("window_s", 15.0))
    clip_sigma = spec.get("clip_sigma", 5.0)

    inp = local_path(cfg, spec["input"])
    expected_path = local_path(cfg, spec["expected"])
    print(f"input     {inp}", file=sys.stderr)
    print(f"expected  {expected_path}", file=sys.stderr)
    print(f"method    {method}", file=sys.stderr)

    ours = subtract_ms(
        inp,
        method=method,
        window_s=window_s,
        clip_sigma=clip_sigma,
        include_flagged=include_flagged,
    )
    exp = open_ms(expected_path)
    try:
        expected = exp.getcol("DATA")
        flag = exp.getcol("FLAG")
    finally:
        exp.close()

    stats = compare(ours, expected, flag)
    print(
        f"unflagged |Δ|  max={stats['max']:.4e}  "
        f"median={stats['median']:.4e}  mean={stats['mean']:.4e}"
    )
    print(f"all rows  |Δ|  max={stats['all_max']:.4e}")

    if args.write is not None:
        dest = (
            inp.with_name(inp.name.replace(".ms", "_ours.ms"))
            if args.write == "auto"
            else Path(args.write)
        )
        write_ms(inp, dest, ours)
        print(dest)

    # Gate: complex64 roundoff on ~kJy visibilities is ≲ 1e-3 Jy.
    ok = stats["max"] < 1e-3
    if not ok:
        print("GATE FAILED: residuals exceed 1e-3 Jy on unflagged visibilities", file=sys.stderr)
        return 1
    print("GATE PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
