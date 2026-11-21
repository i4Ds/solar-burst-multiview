#!/usr/bin/env python3
"""Apply Rohit's Cen A CASA bandpass to the 0.5 s Sun measurement sets.

No P-AIRCARS. No time averaging. Does not modify the archive extracts.

The tables are his ``1133139776-%b*.cal.p`` B Jones solutions: amplitude
identically 1, phase from Cen A, ``applymode=calonly``, ``calwt=False``,
as in his ``applycal.last``.

    python apply_0p5s_rohit_cal.py 84-85
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

import numpy as np
from casatasks import applycal
from casatools import table as casa_table

PAIRS = {
    "84-85": Path(
        "/mnt/nas05/data02/rohit/20151203_MWA/new_ms/108MHz/"
        "1133139776-%b084-085.cal.p"
    ),
    "125-126": Path(
        "/mnt/nas05/data02/rohit/20151203_MWA/new_ms/161MHz/"
        "1133139776-%b125-126.cal.p"
    ),
    "169-170": Path(
        "/mnt/nas05/data02/rohit/20151203_MWA/new_ms/217MHz/"
        "1133139776-%b169-170.cal.p"
    ),
    "187-188": Path(
        "/mnt/nas05/data02/rohit/20151203_MWA/new_ms/239MHz/"
        "1133139776-%b187-188.cal.p"
    ),
}

SCRATCH = Path(f"/scratch/{os.environ['USER']}")
RAW = SCRATCH / "mwa/sharma2020/raw/1133149192"
OUT = SCRATCH / "mwa/sharma2020/raw/cal_0p5s_casa"
CAL_LOCAL = OUT / "caltables"


def inspect(ms: str) -> None:
    tb = casa_table()
    tb.open(ms)
    cols = sorted(tb.colnames())
    print("columns", cols, flush=True)
    if "DATA" in cols and "CORRECTED_DATA" in cols:
        data = tb.getcol("DATA", 0, 64)
        corr = tb.getcol("CORRECTED_DATA", 0, 64)
        d = np.abs(data)
        c = np.abs(corr)
        print(
            f"|DATA| median={float(np.nanmedian(d)):.4g}  "
            f"|CORRECTED_DATA| median={float(np.nanmedian(c)):.4g}  "
            f"median |C|/|D|={float(np.nanmedian(c / np.maximum(d, 1e-12))):.6g}",
            flush=True,
        )
        print(
            "DATA equals CORRECTED_DATA",
            bool(np.allclose(data, corr, equal_nan=True)),
            flush=True,
        )
    elif "CORRECTED_DATA" not in cols:
        print("no CORRECTED_DATA column", flush=True)
    tb.close()


def copy_ms(src: Path, dest: Path) -> None:
    if dest.exists():
        shutil.rmtree(dest)
    flag = Path(str(dest) + ".flagversions")
    if flag.exists():
        shutil.rmtree(flag)
    print(f"copy {src} -> {dest}", flush=True)
    shutil.copytree(src, dest, symlinks=False)


def copy_cal(src: Path, dest: Path) -> Path:
    if dest.exists():
        shutil.rmtree(dest)
    print(f"copy {src} -> {dest}", flush=True)
    shutil.copytree(src, dest, symlinks=False)
    return dest


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("pair", choices=sorted(PAIRS))
    args = p.parse_args(argv)

    pair = args.pair
    src = RAW / f"1133149192_ch{pair}.ms"
    cal_src = PAIRS[pair]
    if not src.is_dir():
        print(f"missing {src}", file=sys.stderr)
        return 1
    if not cal_src.is_dir():
        print(f"missing Rohit cal table {cal_src}", file=sys.stderr)
        return 1

    OUT.mkdir(parents=True, exist_ok=True)
    CAL_LOCAL.mkdir(parents=True, exist_ok=True)
    dest = OUT / f"1133149192_ch{pair}_0p5s.ms"
    cal = copy_cal(cal_src, CAL_LOCAL / cal_src.name)
    copy_ms(src, dest)

    print(f"src={src}", flush=True)
    print(f"cal={cal}", flush=True)
    print(f"dest={dest}", flush=True)

    applycal(
        vis=str(dest),
        gaintable=[str(cal)],
        applymode="calonly",
        calwt=False,
        interp=["nearest,linear"],
        flagbackup=False,
    )
    inspect(str(dest))
    print(f"APPLY_ROHIT_OK {pair}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
