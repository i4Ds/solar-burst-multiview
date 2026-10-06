"""MWA dynamic spectrum from per-coarse-channel measurement sets.

The Sun is resolved on most MWA baselines, so the spectrum is the mean
cross-correlation amplitude, (|XX| + |YY|) / 2, over the shortest baselines.
Autocorrelations are excluded: they are dominated by the receiver.
Uncalibrated amplitudes are fine for a dynamic spectrum once each channel is
normalised by its own median over time, which ``normalised`` does.

    python -m solarburst.dynspec OUT.npz MS [MS ...] [--nbaselines 100]
    python -m solarburst.dynspec OUT.npz PART.npz [PART.npz ...]   # merge

Inside the calculon container (python-casacore is not in the conda env).
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from numpy.typing import NDArray


def shortest_baselines(ms: str, n: int) -> list[tuple[int, int]]:
    from casacore.tables import table

    pos = table(f"{ms}/ANTENNA", ack=False).getcol("POSITION")
    flagged = table(f"{ms}/ANTENNA", ack=False).getcol("FLAG_ROW")
    good = np.flatnonzero(~flagged)
    pairs = [(a, b) for i, a in enumerate(good) for b in good[i + 1:]]
    length = np.array([np.linalg.norm(pos[a] - pos[b]) for a, b in pairs])
    return [pairs[i] for i in np.argsort(length)[:n]]


def ms_dynspec(ms: str, nbaselines: int = 100, use_flags: bool = False) -> tuple[NDArray, NDArray, NDArray]:
    """Return (unix_time [s], freq [MHz], amplitude[nfreq, ntime]) for one MS.

    AOFlagger flags in ASVO products often cut out solar bursts as RFI, so by
    default only exact zeros (missing data) are dropped, not flagged samples.
    """
    from casacore.tables import table, taql

    pairs = shortest_baselines(ms, nbaselines)
    cond = " || ".join(f"(ANTENNA1=={a} && ANTENNA2=={b})" for a, b in pairs)
    t = table(ms, ack=False)
    sel = taql(f"select TIME, DATA, FLAG from $t where {cond}")
    time = sel.getcol("TIME")
    data = sel.getcol("DATA")  # (row, chan, corr) with corr XX, XY, YX, YY
    flag = sel.getcol("FLAG")
    amp = 0.5 * (np.abs(data[..., 0]) + np.abs(data[..., 3]))
    amp[(amp == 0) | (flag[..., 0] | flag[..., 3] if use_flags else False)] = np.nan
    times, inverse = np.unique(time, return_inverse=True)
    out = np.full((amp.shape[1], times.size), np.nan)
    for k in range(times.size):
        rows = inverse == k
        if rows.any():
            with np.errstate(all="ignore"):
                out[:, k] = np.nanmean(amp[rows], axis=0)
    freq = table(f"{ms}/SPECTRAL_WINDOW", ack=False).getcol("CHAN_FREQ")[0] / 1e6
    # MS TIME is MJD seconds (UTC); convert to unix seconds.
    unix = times - 40587.0 * 86400.0
    return unix, freq, out


def merge(parts: list[tuple[NDArray, NDArray, NDArray]]) -> tuple[NDArray, NDArray, NDArray]:
    """Put per-channel, per-obs pieces on one (freq, time) grid; gaps are NaN."""
    times = np.unique(np.concatenate([p[0] for p in parts]))
    freqs = np.unique(np.concatenate([p[1] for p in parts]))
    grid = np.full((freqs.size, times.size), np.nan)
    for t, f, a in parts:
        grid[np.ix_(np.searchsorted(freqs, f), np.searchsorted(times, t))] = a
    return times, freqs, grid


def normalised(grid: NDArray) -> NDArray:
    """Each channel divided by its median over time."""
    with np.errstate(all="ignore"):
        return grid / np.nanmedian(grid, axis=1, keepdims=True)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("out", type=Path)
    p.add_argument("ms", nargs="+")
    p.add_argument("--nbaselines", type=int, default=100)
    p.add_argument("--use-flags", action="store_true", help="drop flagged samples (cuts bursts)")
    args = p.parse_args()
    parts = []
    if args.out.exists():  # accumulate across observations
        old = np.load(args.out)
        parts.append((old["unix"], old["freq_mhz"], old["amp"]))
    for ms in args.ms:
        if ms.endswith(".npz"):
            d = np.load(ms)
            parts.append((d["unix"], d["freq_mhz"], d["amp"]))
        else:
            parts.append(ms_dynspec(ms, args.nbaselines, args.use_flags))
        print(f"{ms}: {parts[-1][2].shape}", flush=True)
    unix, freq, amp = merge(parts)
    np.savez_compressed(args.out, unix=unix, freq_mhz=freq, amp=amp)
    print(f"wrote {args.out}: {amp.shape}")


if __name__ == "__main__":
    main()
