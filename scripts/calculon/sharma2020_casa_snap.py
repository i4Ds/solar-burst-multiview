#!/usr/bin/env python3
"""CASA tclean snapshots matching Sharma & Oberoi 2020 imaging.

Does not read the TIME column (casacore getcol on these 35 GB MS segfaults
in paircars_env). Default timerange is the mid-scan 0.5 s of 1133149192.

    python3 sharma2020_casa_snap.py MS OUT_PREFIX
    python3 sharma2020_casa_snap.py MS OUT_PREFIX --timerange 2015/12/03/03:42:04.0~2015/12/03/03:42:04.5
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from casatasks import exportfits, tclean

PHASECENTER = "J2000 16h40m55.28s -19d40m25.38s"
# Quiet scan 1133149192: 03:39:36–03:44:32 UT. Mid-scan 0.5 s.
DEFAULT_TIMERANGE = "2015/12/03/03:42:04.0~2015/12/03/03:42:04.5"


def image_one(ms: str, prefix: str, timerange: str, niter: int) -> str:
    tclean(
        vis=ms,
        imagename=prefix,
        datacolumn="corrected",
        imsize=[1024, 1024],
        cell="50arcsec",
        phasecenter=PHASECENTER,
        stokes="I",
        specmode="mfs",
        weighting="briggs",
        robust=0.0,
        deconvolver="hogbom",
        niter=niter,
        gain=0.1,
        pblimit=-1.0,
        savemodel="none",
        restoration=True,
        parallel=False,
        timerange=timerange,
        nterms=1,
        interactive=False,
    )
    fits = prefix + ".fits"
    exportfits(imagename=prefix + ".image", fitsimage=fits, overwrite=True)
    return fits


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("ms")
    p.add_argument("out_prefix")
    p.add_argument("--timerange", default=DEFAULT_TIMERANGE)
    p.add_argument("--niter", type=int, default=2500)
    args = p.parse_args(argv)

    prefix = Path(args.out_prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    os.chdir(prefix.parent)
    name = str(prefix) + "_mid"
    print(f"tclean {name}  {args.timerange}", flush=True)
    fits = image_one(args.ms, name, args.timerange, args.niter)
    meta = prefix.parent / (prefix.name + "_snaps.json")
    meta.write_text(
        json.dumps(
            {"ms": args.ms, "timerange": args.timerange, "fits": fits, "niter": args.niter},
            indent=2,
        )
        + "\n"
    )
    print(f"CASA_SNAP_OK meta={meta}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
