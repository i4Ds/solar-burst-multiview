"""Stack P-AIRCARS HPC images (Stokes I) into one cube on a common grid.

    python3 make_cube.py PBCOR_HPC_DIR OUT.npz [--half 2000] [--cell 20]

Output: data[time, freq, y, x] in Jy/beam (primary-beam corrected), plus
times, freqs (MHz), beams (arcsec) and the grid extent in arcsec. Runs in the
calculon container (numpy, scipy, astropy).
"""

import argparse
import glob
import os
import re

import numpy as np
from astropy.io import fits
from scipy.ndimage import map_coordinates


def main():
    p = argparse.ArgumentParser()
    p.add_argument("hpcdir")
    p.add_argument("out")
    p.add_argument("--half", type=float, default=2000.0)
    p.add_argument("--cell", type=float, default=20.0)
    a = p.parse_args()

    files = sorted(glob.glob(os.path.join(a.hpcdir, "time_*_pol_I_pbcor_HPC.fits")))
    keys = []
    for f in files:
        m = re.search(r"time_(\d{14}\.\d)_freq_([\d.]+)_", os.path.basename(f))
        keys.append((m.group(1), float(m.group(2)), f))
    times = sorted({k[0] for k in keys})
    freqs = sorted({k[1] for k in keys})
    axis = np.arange(-a.half, a.half + a.cell / 2, a.cell)
    X, Y = np.meshgrid(axis, axis)
    cube = np.full((len(times), len(freqs), axis.size, axis.size), np.nan, dtype=np.float32)
    beams = np.full((len(freqs), 3), np.nan)
    for t, fmhz, f in keys:
        with fits.open(f) as h:
            d = np.squeeze(h[0].data).astype(float)
            hd = h[0].header
        d = d[0] if d.ndim == 3 else d
        px = (X - hd["CRVAL1"]) / hd["CDELT1"] + hd["CRPIX1"] - 1
        py = (Y - hd["CRVAL2"]) / hd["CDELT2"] + hd["CRPIX2"] - 1
        cube[times.index(t), freqs.index(fmhz)] = map_coordinates(d, [py, px], order=1, cval=np.nan)
        beams[freqs.index(fmhz)] = [hd["BMAJ"] * 3600, hd["BMIN"] * 3600, hd["BPA"]]
    np.savez_compressed(a.out, data=cube, times=np.array(times), freqs=np.array(freqs),
                        beams=beams, extent=np.array([axis[0] - a.cell / 2, axis[-1] + a.cell / 2] * 2))
    print(f"wrote {a.out}: {cube.shape} times {times[0]}..{times[-1]} freqs {freqs[0]}..{freqs[-1]} MHz")


if __name__ == "__main__":
    main()
