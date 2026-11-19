#!/usr/bin/env python3
"""Phase-only CASA bandpass on Cen A, then applycal on the 0.5 s Sun.

Same step as Rohit's ``.cal.p`` tables: B Jones with |g| identically 1,
``applymode=calonly``, ``calwt=False``. No P-AIRCARS. Does not modify the
archive extracts.

    python solve_cena_bandpass.py 84-85
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

import numpy as np
from casatasks import applycal, bandpass
from casatools import table as casa_table

PAIRS = ("84-85", "125-126", "169-170", "187-188")
SCRATCH = Path(f"/scratch/{os.environ['USER']}")
SUN_OBS = os.environ.get("SUN_OBS", "1133236216")
CAL_OBS = os.environ.get("CAL_OBS", "1133236576")
RAW = Path(os.environ.get("RAW_ROOT", str(SCRATCH / "mwa/quiet_noon" / SUN_OBS)))
CAL_RAW = Path(os.environ.get("CAL_ROOT", str(SCRATCH / "mwa/quiet_noon" / CAL_OBS)))
OUT = Path(os.environ.get("CAL_OUT", str(SCRATCH / "mwa/quiet_noon/cal_0p5s_casa")))


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


def refant(ms: str) -> str:
    tb = casa_table()
    tb.open(ms + "/ANTENNA")
    names = list(tb.getcol("NAME"))
    tb.close()
    for want in ("Tile011", "Tile012", "Tile013"):
        if want in names:
            return want
    return str(names[0])


def force_unit_amp(caltable: Path) -> None:
    tb = casa_table()
    tb.open(str(caltable), nomodify=False)
    g = np.asarray(tb.getcol("CPARAM"), dtype=np.complex128)
    amp = np.abs(g)
    amp[amp == 0] = 1.0
    tb.putcol("CPARAM", (g / amp).astype(g.dtype))
    tb.close()
    tb.open(str(caltable))
    g2 = np.abs(tb.getcol("CPARAM"))
    tb.close()
    print(
        f"|g| after unit-amp  min={float(np.nanmin(g2)):.6g}  "
        f"max={float(np.nanmax(g2)):.6g}",
        flush=True,
    )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("pair", choices=PAIRS)
    args = p.parse_args(argv)

    pair = args.pair
    sun_src = RAW / f"{SUN_OBS}_ch{pair}.ms"
    cal_src = CAL_RAW / f"{CAL_OBS}_ch{pair}.ms"
    if not sun_src.is_dir():
        print(f"missing {sun_src}", file=sys.stderr)
        return 1
    if not cal_src.is_dir():
        print(f"missing {cal_src}", file=sys.stderr)
        return 1

    OUT.mkdir(parents=True, exist_ok=True)
    caltab_dir = OUT / "caltables"
    caltab_dir.mkdir(parents=True, exist_ok=True)
    dest = OUT / f"{SUN_OBS}_ch{pair}_0p5s.ms"
    caltab = caltab_dir / f"{CAL_OBS}-ch{pair}.cal.p"
    if caltab.exists():
        shutil.rmtree(caltab)
    copy_ms(sun_src, dest)

    ant = refant(str(cal_src))
    print(f"refant={ant}  cal={cal_src}  sun={dest}", flush=True)
    bandpass(
        vis=str(cal_src),
        caltable=str(caltab),
        solint="inf",
        combine="scan",
        refant=ant,
        minblperant=4,
        minsnr=3.0,
        solnorm=False,
        bandtype="B",
        degamp=0,
        degphase=0,
    )
    force_unit_amp(caltab)

    applycal(
        vis=str(dest),
        gaintable=[str(caltab)],
        applymode="calonly",
        calwt=False,
        interp=["nearest,linear"],
        flagbackup=False,
    )
    inspect(str(dest))
    print(f"APPLY_PHASE_BANDPASS_OK {pair}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
