"""Quiet-Sun flux-scale check of P-AIRCARS images.

For each coarse channel, averages the primary-beam corrected HPC images whose
time stamps fall in [T0, T1] and reports
  * S_tot: flux density within R_TOT solar radii (Jy), sum(I) / beam area;
  * T_B quiet disk: median brightness temperature within 0.8 R_sun, outside
    EXCL_R arcsec of the noise-storm source at (EXCL_X, EXCL_Y);
  * the flux density a uniform disk of radius 1.1 R_sun would have at 0.5 and
    1 MK, the usual quiet-Sun range at 100-200 MHz.

    python3 quiet_sun_flux.py PBCOR_HPC_DIR OUT_PREFIX --t0 20220930043124 --t1 20220930043140

Runs in the calculon container (numpy, astropy, matplotlib).
"""

import argparse
import glob
import json
import os
import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from astropy.io import fits

K_B, C = 1.380649e-23, 299792458.0
RSUN_ARCSEC = 958.0  # 2022-09-30


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("hpcdir")
    p.add_argument("out")
    p.add_argument("--t0", required=True)
    p.add_argument("--t1", required=True)
    p.add_argument("--r-tot", type=float, default=2.0)
    p.add_argument("--excl-x", type=float, default=300.0)
    p.add_argument("--excl-y", type=float, default=100.0)
    p.add_argument("--excl-r", type=float, default=400.0)
    a = p.parse_args()

    files = sorted(glob.glob(os.path.join(a.hpcdir, "time_*_freq_*_pol_I_pbcor_HPC.fits")))
    groups = {}
    for f in files:
        m = re.search(r"time_(\d{14})\.\d_freq_([\d.]+)_", os.path.basename(f))
        if m and a.t0 <= m.group(1) <= a.t1:
            groups.setdefault(float(m.group(2)), []).append(f)
    rows = []
    for fmhz, fl in sorted(groups.items()):
        stack = []
        for f in fl:
            with fits.open(f) as h:
                d = np.squeeze(h[0].data).astype(float)
                hd = h[0].header
            stack.append(d[0] if d.ndim == 3 else d)
        img = np.nanmean(stack, axis=0)
        ny, nx = img.shape
        y, x = np.mgrid[:ny, :nx]
        X = (x + 1 - hd["CRPIX1"]) * hd["CDELT1"] + hd["CRVAL1"]
        Y = (y + 1 - hd["CRPIX2"]) * hd["CDELT2"] + hd["CRVAL2"]
        R = np.hypot(X, Y)
        bmaj, bmin = hd["BMAJ"] * 3600, hd["BMIN"] * 3600
        beam_px = np.pi * bmaj * bmin / (4 * np.log(2)) / (hd["CDELT1"] * hd["CDELT2"])
        s_tot = float(np.nansum(img[R < a.r_tot * RSUN_ARCSEC]) / beam_px)
        nu = fmhz * 1e6
        omega_beam = np.pi * np.radians(bmaj / 3600) * np.radians(bmin / 3600) / (4 * np.log(2))
        tb = img * 1e-26 * C**2 / (2 * K_B * nu**2 * omega_beam)
        quiet = (R < 0.8 * RSUN_ARCSEC) & (np.hypot(X - a.excl_x, Y - a.excl_y) > a.excl_r)
        omega_disk = np.pi * np.radians(1.1 * RSUN_ARCSEC / 3600) ** 2
        s_exp = [2 * K_B * nu**2 / C**2 * t * omega_disk / 1e-26 for t in (0.5e6, 1.0e6)]
        rows.append(dict(freq_mhz=fmhz, n_images=len(fl), s_tot_jy=s_tot,
                         tb_quiet_disk_mk=float(np.nanmedian(tb[quiet]) / 1e6),
                         tb_peak_mk=float(np.nanmax(tb) / 1e6), s_expected_0p5_1mk_jy=s_exp,
                         beam_arcsec=[bmaj, bmin]))
        print(f"{fmhz:7.2f} MHz  n={len(fl)}  S_tot={s_tot:9.3g} Jy  T_B(quiet disk)={rows[-1]['tb_quiet_disk_mk']:.2f} MK"
              f"  expected S(0.5-1 MK disk)={s_exp[0]:.3g}-{s_exp[1]:.3g} Jy")
    with open(a.out + ".json", "w") as f:
        json.dump(rows, f, indent=1)
    if rows:
        fq = np.array([r["freq_mhz"] for r in rows])
        fig, axs = plt.subplots(1, 2, figsize=(12, 4.8))
        axs[0].plot(fq, [r["s_tot_jy"] for r in rows], "o-", label=f"P-AIRCARS, within {a.r_tot} R☉")
        axs[0].fill_between(fq, [r["s_expected_0p5_1mk_jy"][0] for r in rows],
                            [r["s_expected_0p5_1mk_jy"][1] for r in rows], alpha=0.3, label="1.1 R☉ disk, 0.5–1 MK")
        axs[0].set_yscale("log"); axs[0].set_xlabel("MHz"); axs[0].set_ylabel("Jy"); axs[0].legend()
        axs[1].plot(fq, [r["tb_quiet_disk_mk"] for r in rows], "o-")
        axs[1].axhspan(0.5, 1.0, alpha=0.3)
        axs[1].set_xlabel("MHz"); axs[1].set_ylabel("median T_B, quiet disk [MK]")
        fig.suptitle(f"Quiet-Sun check, {a.t0}–{a.t1}")
        fig.tight_layout(); fig.savefig(a.out + ".png", dpi=110)


if __name__ == "__main__":
    main()
