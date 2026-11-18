#!/usr/bin/env python3
"""One 0.5 s SuperUniform snapshot: Rohit's CORRECTED_DATA vs our applycal set.

Same time, same CASA numbers, same coarse channel (84). Not Figure 4.
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
from casatasks import exportfits, rmtables, tclean
from casatools import msmetadata

PHASECENTER = "J2000 16h40m55.28s -19d40m25.38s"
TRANGE = "2015/12/03/03:42:04.0~2015/12/03/03:42:04.5"
ROHIT = "/mnt/nas05/data02/rohit/20151203_MWA/new_ms/108MHz/1133149192-084-085.ms"
OURS = f"/scratch/{os.environ['USER']}/mwa/sharma2020/raw/cal_0p5s/1133149192_ch84_0p5s.ms"
OUT = Path(f"/scratch/{os.environ['USER']}/mwa/sharma2020/raw/cal_0p5s/inspect")


def chanfreqs(ms: str) -> np.ndarray:
    md = msmetadata()
    md.open(ms)
    freqs = np.asarray(md.chanfreqs(0))
    md.close()
    md.done()
    return freqs


def matching_spw(rohit: str, ours: str) -> str:
    rf = chanfreqs(rohit)
    of = chanfreqs(ours)
    lo, hi = float(of.min()), float(of.max())
    idx = [i for i, f in enumerate(rf) if lo - 1e3 <= f <= hi + 1e3]
    if not idx:
        raise RuntimeError(f"no Rohit channels in {lo}-{hi} Hz")
    spw = f"0:{min(idx)}~{max(idx)}"
    print(
        f"ours {of.size} chans {of.min()/1e6:.4f}-{of.max()/1e6:.4f} MHz",
        flush=True,
    )
    print(
        f"rohit spw={spw} {rf[min(idx)]/1e6:.4f}-{rf[max(idx)]/1e6:.4f} MHz "
        f"({len(idx)} of {rf.size})",
        flush=True,
    )
    return spw


def image(ms: str, prefix: Path, spw: str) -> Path:
    for suf in (".image", ".model", ".psf", ".residual", ".pb", ".sumwt", ".mask"):
        rmtables(str(prefix) + suf)
    tclean(
        vis=ms,
        imagename=str(prefix),
        datacolumn="corrected",
        spw=spw,
        imsize=[1024, 1024],
        cell="50arcsec",
        phasecenter=PHASECENTER,
        stokes="I",
        specmode="mfs",
        weighting="superuniform",
        npixels=0,
        deconvolver="hogbom",
        niter=8000,
        gain=0.1,
        threshold=0.0,
        pblimit=-1.0,
        savemodel="none",
        restoration=True,
        parallel=False,
        timerange=TRANGE,
        nterms=1,
        interactive=False,
    )
    fits_path = Path(str(prefix) + ".fits")
    exportfits(imagename=str(prefix) + ".image", fitsimage=str(fits_path), overwrite=True)
    print(f"wrote {fits_path}", flush=True)
    return fits_path


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    os.chdir(OUT)
    spw = matching_spw(ROHIT, OURS)
    image(ROHIT, OUT / "rohit_ch84_034204", spw)
    image(OURS, OUT / "ours_ch84_034204", "")
    print("COMPARE_SNAP_OK", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
