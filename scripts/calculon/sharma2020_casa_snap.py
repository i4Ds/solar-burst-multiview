#!/usr/bin/env python3
"""One 0.5 s CASA image matching Rohit's published FITS HISTORY.

The FITS that became Sharma & Oberoi 2020 Fig. 4 were written by
CASA 5.3.0-143 ``imager::clean()`` (not tclean):

    1024², 50″, Stokes I, MFS
    SuperUniform (uv cell [-3, 3])
    multifield Hogbom
    gain 0.1, niter 8000, threshold 0 mJy
    phasecentre J2000 16h40m55.28s −19d40m25.38s
    uvrange empty

This script uses classic ``clean`` when the environment still has it,
else ``tclean`` with the same numbers. Writes under the given prefix.
Does not touch Rohit's tree.

    python3 sharma2020_casa_snap.py MS OUT_PREFIX
    python3 sharma2020_casa_snap.py MS OUT_PREFIX --timerange 2015/12/03/03:42:04.0~2015/12/03/03:42:04.5
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from casatasks import exportfits

try:
    from casatasks import clean as casa_clean
except ImportError:
    casa_clean = None
from casatasks import tclean

PHASECENTER = "J2000 16h40m55.28s -19d40m25.38s"
DEFAULT_TIMERANGE = "2015/12/03/03:42:04.0~2015/12/03/03:42:04.5"
NITER = 8000
GAIN = 0.1


def image_clean(ms: str, prefix: str, timerange: str, niter: int) -> None:
    """Classic imager::clean — this is what wrote the published FITS."""
    casa_clean(
        vis=ms,
        imagename=prefix,
        mode="mfs",
        niter=niter,
        gain=GAIN,
        threshold="0mJy",
        psfmode="hogbom",
        imagermode="",
        imsize=[1024],
        cell=["50arcsec"],
        stokes="I",
        weighting="superuniform",
        npixels=0,
        uvrange="",
        phasecenter=PHASECENTER,
        timerange=timerange,
        interactive=False,
        usescratch=False,
        mask="",
    )


def image_tclean(ms: str, prefix: str, timerange: str, niter: int) -> None:
    """Fallback if this CASA build dropped the classic clean task."""
    tclean(
        vis=ms,
        imagename=prefix,
        datacolumn="corrected",
        imsize=[1024, 1024],
        cell="50arcsec",
        phasecenter=PHASECENTER,
        stokes="I",
        specmode="mfs",
        weighting="superuniform",
        npixels=0,
        deconvolver="hogbom",
        niter=niter,
        gain=GAIN,
        threshold=0.0,
        pblimit=-1.0,
        savemodel="none",
        restoration=True,
        parallel=False,
        timerange=timerange,
        uvrange="",
        nterms=1,
        interactive=False,
    )


def image_one(ms: str, prefix: str, timerange: str, niter: int) -> tuple[str, str]:
    task = "clean" if casa_clean is not None else "tclean"
    print(f"{task} {prefix}  niter={niter}  superuniform  hogbom  {timerange}", flush=True)
    if casa_clean is not None:
        image_clean(ms, prefix, timerange, niter)
        image_name = prefix + ".image"
    else:
        image_tclean(ms, prefix, timerange, niter)
        image_name = prefix + ".image"
    fits = prefix + ".fits"
    exportfits(imagename=image_name, fitsimage=fits, overwrite=True)
    return fits, task


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("ms")
    p.add_argument("out_prefix")
    p.add_argument("--timerange", default=DEFAULT_TIMERANGE)
    p.add_argument("--niter", type=int, default=NITER)
    args = p.parse_args(argv)

    prefix = Path(args.out_prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    os.chdir(prefix.parent)
    name = str(prefix) + "_mid"
    fits, task = image_one(args.ms, name, args.timerange, args.niter)
    meta = prefix.parent / (prefix.name + "_snaps.json")
    meta.write_text(
        json.dumps(
            {
                "ms": args.ms,
                "timerange": args.timerange,
                "fits": fits,
                "niter": args.niter,
                "gain": GAIN,
                "weighting": "superuniform",
                "psfmode": "hogbom",
                "task": task,
                "phasecenter": PHASECENTER,
            },
            indent=2,
        )
        + "\n"
    )
    print(f"CASA_SNAP_OK task={task} meta={meta}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
