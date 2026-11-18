#!/usr/bin/env python3
"""Apply existing Cen A bandpass tables to the 0.5 s Sun measurement sets.

No time averaging. No imaging. Does not modify the extracted archive sets.
Uses casatasks only (casacore.tables plus casatasks segfaults on this cluster).

    python apply_0p5s_bcal.py 84
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import numpy as np
from casatasks import applycal, mstransform
from casatools import msmetadata

PAIRS = {
    84: "84-85",
    85: "84-85",
    125: "125-126",
    126: "125-126",
    169: "169-170",
    170: "169-170",
    187: "187-188",
    188: "187-188",
}

SCRATCH = Path(f"/scratch/{os.environ['USER']}")
RAW = SCRATCH / "mwa/sharma2020/raw/1133149192"
CALDIR = SCRATCH / "paircars/out/fig4_raw/20151203/calibrators/caltables"
OUT = SCRATCH / "mwa/sharma2020/raw/cal_0p5s"


def freq_to_mwa_coarse(freq_mhz: float) -> int:
    grid = np.arange(255) * 1.28
    return int(np.where(np.round(np.abs(freq_mhz - grid), 2) == np.min(np.round(np.abs(freq_mhz - grid), 2)))[0][-1])


def bcal_for(ch: int) -> Path:
    att = CALDIR / f"calibrator_1133139776_ch_{ch}.bcal.att14.0"
    plain = CALDIR / f"calibrator_1133139776_ch_{ch}.bcal"
    if att.exists():
        return att
    if plain.exists():
        return plain
    raise FileNotFoundError(f"no bandpass table for coarse channel {ch} in {CALDIR}")


def spw_for(ms: str, ch: int) -> str:
    md = msmetadata()
    md.open(ms)
    freqs = np.asarray(md.chanfreqs(0)) / 1e6
    md.close()
    md.done()
    idx = [i for i, f in enumerate(freqs) if freq_to_mwa_coarse(float(f)) == ch]
    if not idx:
        raise ValueError(f"{ms} has no fine channels for coarse {ch}")
    return f"0:{min(idx)}~{max(idx)}"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("channel", type=int, choices=sorted(PAIRS))
    args = p.parse_args(argv)

    ch = args.channel
    src = RAW / f"1133149192_ch{PAIRS[ch]}.ms"
    if not src.is_dir():
        print(f"missing {src}", file=sys.stderr)
        return 1
    bcal = bcal_for(ch)
    OUT.mkdir(parents=True, exist_ok=True)
    dest = OUT / f"1133149192_ch{ch}_0p5s.ms"
    if dest.exists():
        os.system(f"rm -rf {dest} {dest}.flagversions")

    spw = spw_for(str(src), ch)
    print(f"src={src}", flush=True)
    print(f"spw={spw}", flush=True)
    print(f"bcal={bcal}", flush=True)
    print(f"dest={dest}", flush=True)

    mstransform(
        vis=str(src),
        outputvis=str(dest),
        spw=spw,
        datacolumn="data",
        timeaverage=False,
        chanaverage=False,
    )
    applycal(
        vis=str(dest),
        gaintable=[str(bcal)],
        applymode="calflag",
        interp=["linear,linear"],
        calwt=[False],
        flagbackup=False,
    )
    print(f"APPLY_0P5S_OK ch{ch}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
