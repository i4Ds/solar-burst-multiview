#!/usr/bin/env python3
"""0.5 s CASA SuperUniform images for one quiet-Sun noon scan.

Same numbers as Sharma & Oberoi 2020 Figure 4 (FITS HISTORY): 1024², 50″,
Stokes I, MFS, SuperUniform, Hogbom, gain 0.1, niter 8000. Phase centre is
this observation's pointing (metafits RA/DEC), not the 3 December 2015
coordinates. Classic ``clean`` when present, else ``tclean``.

    python quiet_noon_casa_snap.py MS OUT_PREFIX --metafits OBS.metafits --all-frames
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path

from astropy.io import fits
from casatasks import exportfits

try:
    from casatasks import clean as casa_clean
except ImportError:
    casa_clean = None
from casatasks import tclean

NITER = 8000
GAIN = 0.1
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


def pointing_phasecenter(metafits: Path) -> str:
    """CASA phasecentre string from the metafits pointing (Rohit's convention)."""
    hdr = fits.getheader(metafits)
    ra = float(hdr["RA"])
    dec = float(hdr["DEC"])
    ra_h = ra / 15.0
    rh = int(ra_h)
    rm = int((ra_h - rh) * 60.0)
    rs = ((ra_h - rh) * 60.0 - rm) * 60.0
    sign = "-" if dec < 0 else "+"
    ad = abs(dec)
    dd = int(ad)
    dm = int((ad - dd) * 60.0)
    ds = ((ad - dd) * 60.0 - dm) * 60.0
    return f"J2000 {rh:02d}h{rm:02d}m{rs:05.2f}s {sign}{dd:02d}d{dm:02d}m{ds:05.2f}s"


def scan_start_from_metafits(metafits: Path) -> datetime:
    hdr = fits.getheader(metafits)
    raw = str(hdr["DATE-OBS"])
    if raw.endswith("Z"):
        raw = raw[:-1]
    return datetime.fromisoformat(raw).replace(tzinfo=None)


def n_frames_from_metafits(metafits: Path) -> int:
    hdr = fits.getheader(metafits)
    exp = float(hdr.get("EXPOSURE") or hdr.get("DURATION") or 296.0)
    return int(round(exp / 0.5))


def casa_timerange(start: datetime, i: int) -> str:
    t0 = start + timedelta(seconds=0.5 * i)
    t1 = t0 + timedelta(seconds=0.5)
    fmt = "%Y/%m/%d/%H:%M:%S.%f"
    a, b = t0.strftime(fmt)[:-5], t1.strftime(fmt)[:-5]
    return f"{a}~{b}"


def rmtables(prefix: str) -> None:
    for suf in CASA_SUFFIXES:
        p = Path(prefix + suf)
        if p.is_dir():
            shutil.rmtree(p, ignore_errors=True)
        elif p.exists():
            p.unlink()


def image_clean(ms: str, prefix: str, timerange: str, niter: int, phasecenter: str) -> None:
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
        phasecenter=phasecenter,
        timerange=timerange,
        interactive=False,
        usescratch=False,
        mask="",
    )


def image_tclean(ms: str, prefix: str, timerange: str, niter: int, phasecenter: str) -> None:
    tclean(
        vis=ms,
        imagename=prefix,
        datacolumn="corrected",
        imsize=[1024, 1024],
        cell="50arcsec",
        phasecenter=phasecenter,
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


def image_one(
    ms: str, prefix: str, timerange: str, niter: int, phasecenter: str
) -> tuple[str, str]:
    task = "clean" if casa_clean is not None else "tclean"
    print(
        f"{task} {prefix}  niter={niter}  superuniform  hogbom  {timerange}  {phasecenter}",
        flush=True,
    )
    if casa_clean is not None:
        image_clean(ms, prefix, timerange, niter, phasecenter)
    else:
        image_tclean(ms, prefix, timerange, niter, phasecenter)
    fits_path = prefix + ".fits"
    exportfits(imagename=prefix + ".image", fitsimage=fits_path, overwrite=True)
    return fits_path, task


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("ms")
    p.add_argument("out_prefix")
    p.add_argument("--metafits", type=Path, required=True)
    p.add_argument("--niter", type=int, default=NITER)
    p.add_argument("--all-frames", action="store_true")
    p.add_argument("--start", type=int, default=0)
    p.add_argument("--stop", type=int, default=None)
    args = p.parse_args(argv)

    phasecenter = pointing_phasecenter(args.metafits)
    scan_start = scan_start_from_metafits(args.metafits)
    n_frames = n_frames_from_metafits(args.metafits)
    stop = n_frames if args.stop is None else args.stop
    prefix = Path(args.out_prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    os.chdir(prefix.parent)
    print(
        f"DATE-OBS {scan_start.isoformat()}  n_frames={n_frames}  phasecenter={phasecenter}",
        flush=True,
    )

    if not args.all_frames:
        mid = n_frames // 2
        tr = casa_timerange(scan_start, mid)
        name = str(prefix) + "_mid"
        fits, task = image_one(args.ms, name, tr, args.niter, phasecenter)
        meta = prefix.parent / (prefix.name + "_snaps.json")
        meta.write_text(
            json.dumps(
                {
                    "ms": args.ms,
                    "timerange": tr,
                    "fits": fits,
                    "niter": args.niter,
                    "gain": GAIN,
                    "weighting": "superuniform",
                    "psfmode": "hogbom",
                    "task": task,
                    "phasecenter": phasecenter,
                    "n_frames": n_frames,
                },
                indent=2,
            )
            + "\n"
        )
        print(f"CASA_SNAP_OK task={task} meta={meta}")
        return 0

    work = str(prefix) + "_work"
    n_ok = 0
    for i in range(args.start, stop):
        idx = INDEX0 + i
        dest = prefix.parent / f"{prefix.name}_{idx:04d}.fits"
        if dest.exists() and dest.stat().st_size > 1000:
            n_ok += 1
            continue
        tr = casa_timerange(scan_start, i)
        rmtables(work)
        print(f"FRAME {idx:04d} {i - args.start + 1}/{stop - args.start}  {tr}", flush=True)
        try:
            fits_path, task = image_one(args.ms, work, tr, args.niter, phasecenter)
        except RuntimeError as exc:
            rmtables(work)
            print(f"FRAME_SKIP {idx:04d}  {exc}", flush=True)
            continue
        shutil.move(fits_path, dest)
        rmtables(work)
        n_ok += 1
        print(f"FRAME_OK {dest}  have={n_ok}", flush=True)
    print(f"CASA_ALL_OK {prefix.name}  {n_ok}/{stop - args.start}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
