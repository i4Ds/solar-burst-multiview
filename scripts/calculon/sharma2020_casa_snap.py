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
import shutil
from datetime import datetime, timedelta
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
# First integration in the FITS is DATE-OBS 03:39:37.25. 03:39:36 is empty
# in the MS. Frame 294 at this start is 03:42:04 (the mid-scan snapshot that
# already worked). Rohit's 570 files are .0010 … .0579.
SCAN_START = datetime(2015, 12, 3, 3, 39, 37)
N_FRAMES = 570
INDEX0 = 10
CASA_SUFFIXES = (
    ".image",
    ".model",
    ".psf",
    ".residual",
    ".pb",
    ".sumwt",
    ".mask",
    ".flux",
    ".workdirectory",
)


def casa_timerange(i: int) -> str:
    t0 = SCAN_START + timedelta(seconds=0.5 * i)
    t1 = t0 + timedelta(seconds=0.5)
    fmt = "%Y/%m/%d/%H:%M:%S.%f"
    a, b = t0.strftime(fmt)[:-5], t1.strftime(fmt)[:-5]  # one decimal
    return f"{a}~{b}"


def rmtables(prefix: str) -> None:
    for suf in CASA_SUFFIXES:
        p = Path(prefix + suf)
        if p.is_dir():
            shutil.rmtree(p, ignore_errors=True)
        elif p.exists():
            p.unlink()


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
    p.add_argument(
        "--all-frames",
        action="store_true",
        help=f"image all {N_FRAMES} half-second frames (Figure 4 is their mean)",
    )
    p.add_argument("--start", type=int, default=0)
    p.add_argument("--stop", type=int, default=N_FRAMES)
    args = p.parse_args(argv)

    prefix = Path(args.out_prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    os.chdir(prefix.parent)

    if not args.all_frames:
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

    work = str(prefix) + "_work"
    n_ok = 0
    for i in range(args.start, args.stop):
        idx = INDEX0 + i
        dest = prefix.parent / f"{prefix.name}_{idx:04d}.fits"
        if dest.exists() and dest.stat().st_size > 1000:
            n_ok += 1
            continue
        tr = casa_timerange(i)
        rmtables(work)
        print(f"FRAME {idx:04d} {i - args.start + 1}/{args.stop - args.start}  {tr}", flush=True)
        try:
            fits, task = image_one(args.ms, work, tr, args.niter)
        except RuntimeError as exc:
            rmtables(work)
            print(f"FRAME_SKIP {idx:04d}  {exc}", flush=True)
            continue
        shutil.move(fits, dest)
        rmtables(work)
        n_ok += 1
        print(f"FRAME_OK {dest}  have={n_ok}", flush=True)
    print(f"CASA_ALL_OK {prefix.name}  {n_ok}/{args.stop - args.start}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
