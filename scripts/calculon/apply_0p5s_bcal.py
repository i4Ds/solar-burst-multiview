#!/usr/bin/env python3
"""Apply existing Cen A bandpass tables to the 0.5 s Sun measurement sets.

No time averaging. No imaging. Writes CORRECTED_DATA at the native 0.5 s
cadence. Does not modify the extracted archive sets.

    python apply_0p5s_bcal.py 84
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import numpy as np
from astropy.time import Time
from casacore.tables import table
from casatasks import applycal, mstransform

from paircars.utils.mwa_utils import get_MWA_coarse_bands, get_MWA_coarse_chan

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

SCRATCH = Path(os.environ.get("SCRATCH_PAIRCARS", f"/scratch/{os.environ['USER']}"))
RAW = SCRATCH / "mwa/sharma2020/raw/1133149192"
CALDIR = (
    SCRATCH
    / "paircars/out/fig4_raw/20151203/calibrators/caltables"
)
OUT = SCRATCH / "mwa/sharma2020/raw/cal_0p5s"


def report_time(ms: str) -> None:
    t = table(ms, ack=False)
    time = np.unique(t.getcol("TIME"))
    interval = np.unique(np.round(t.getcol("INTERVAL"), 4))
    t.close()
    print(
        f"TIME n={len(time)}  "
        f"{Time(time[0] / 86400.0, format='mjd').iso} .. "
        f"{Time(time[-1] / 86400.0, format='mjd').iso}  "
        f"dt={float(np.median(np.diff(time))) if len(time) > 1 else 0:.4f}s  "
        f"INTERVAL={interval.tolist()}"
    )


def bcal_for(ch: int) -> Path:
    att = CALDIR / f"calibrator_1133139776_ch_{ch}.bcal.att14.0"
    plain = CALDIR / f"calibrator_1133139776_ch_{ch}.bcal"
    if att.exists():
        return att
    if plain.exists():
        return plain
    raise FileNotFoundError(f"no bandpass table for coarse channel {ch} in {CALDIR}")


def spw_for(ms: str, ch: int) -> str:
    chans = get_MWA_coarse_chan(ms)
    bands = get_MWA_coarse_bands(ms)
    if ch not in chans:
        raise ValueError(f"{ms} has coarse channels {chans}, not {ch}")
    start, end, good = bands[chans.index(ch)]
    return f"0:{min(good)}~{max(good)}"


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
    print(f"src={src}")
    print(f"spw={spw}")
    print(f"bcal={bcal}")
    print(f"dest={dest}")
    report_time(str(src))

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
    report_time(str(dest))
    t = table(str(dest), ack=False)
    cols = t.colnames()
    t.close()
    if "CORRECTED_DATA" not in cols:
        print("no CORRECTED_DATA after applycal", file=sys.stderr)
        return 1
    print(f"APPLY_0P5S_OK ch{ch}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
