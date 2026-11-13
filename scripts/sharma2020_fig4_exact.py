#!/usr/bin/env python3
"""Sharma & Oberoi 2020 Figure 4 — the paper's images, the paper's kelvin.

This is the script to run if you want the 2020 figure, not a 2022 shortcut.

    python scripts/sharma2020_fig4_exact.py
    python scripts/sharma2020_fig4_exact.py --reuse   # skip re-reading the FITS

Does not overwrite figures/sharma2020/fig4.png (that PNG is the 9.48 plot).


What 9.48 is, and why it is not used here
-----------------------------------------
CASA writes maps in Jy/beam. Those numbers are *not* on an absolute flux
scale: antenna gains set an arbitrary zero. To plot million-K, you still
need one stretch that makes the disk equal the true whole-Sun flux.

Sharma et al. 2022 stored already-stretched cubes (the pickles in Tb_new/).
When we converted the same CASA FITS with the textbook Rayleigh–Jeans
formula (Mohan & Oberoi 2017 Eq. 4, restoring beam from BMAJ/BMIN), the
pickles were 9.48× brighter at 108 MHz, frame 0010. So we multiplied every
map by 9.48 to match the 2022 caption. That is ``imaging.tb_scale``.

Incentive: match the 2022 stored cubes without computing the stretch.
What it brings: the 2022 Figure 3 peaks. Nothing else. It is one number,
frozen, applied to every frequency and every day. It is not a calibration.

The 2020 paper does not use it. It computes the stretch properly:

    F(ν) = S_⊙ / (integral of the map over the 5σ radio Sun)

S_⊙ comes from Oberoi, Sharma & Rogers (2017) on the visibilities, not
from the map. F(ν) on this quiet scan is ~11–13, the same *kind* of
number as 9.48, but measured per band from this observation.


What “exactly the same images” means
------------------------------------
The paper's images already exist: Rohit's CASA 0.5 s × 2 MHz FITS for
scan 1133149192. Section 4: CASA, then Mohan & Oberoi (2017) T_B, then
the time-mean of those T_B maps.

This script uses those FITS. Re-running tclean (or WSClean) makes a *new*
picture. Similar shape; not the same file. The CASA recipe, if you need
an independent remake, is scripts/calculon/sharma2020_casa_snap.py
(1024², 50″, Briggs 0, Hogbom niter 2500, gain 0.1). That remake is not
what Figure 4 was published from.

Known leftovers versus the letter of the papers
-----------------------------------------------
- One F(ν) on the 4-minute mean map, not F(ν) on each 0.5 s frame then
  a mean of T_B. For a quiet Sun the two are close; the paper's wording
  is the per-frame route.
- S_⊙ uses Haslam 1982 at this pointing and a 4×4 array-factor tile beam,
  not Oberoi's unpublished FEKO patterns.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from solarburst.config import REPO_ROOT
from solarburst.mohan2017 import scale_image

# Plotting and FITS averaging live next to this file; not a package.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import sharma2020_fig4 as fig4  # noqa: E402
import sharma2020_paper_tb as paper_tb  # noqa: E402

CAPTION_MK = {"108": 0.92, "162": 1.20, "217": 1.50, "240": None}
FUDGE_2022 = 9.48


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--config", default="sharma2022")
    p.add_argument(
        "--flux-dir",
        type=Path,
        default=REPO_ROOT / "data" / "quiet2015" / "paper_flux",
    )
    p.add_argument("--reuse", action="store_true")
    p.add_argument("--nsig", type=float, default=5.0)
    p.add_argument(
        "--out",
        type=Path,
        default=REPO_ROOT / "figures" / "sharma2020" / "fig4_paper.png",
    )
    args = p.parse_args(argv)

    print(
        "Sharma & Oberoi 2020 Fig. 4\n"
        "  images : Rohit's CASA 0.5 s FITS (already made; we do not image)\n"
        "  kelvin : Oberoi 2017 S_⊙ → Mohan 2017 F(ν) → Rayleigh–Jeans\n"
        f"  unused : imaging.tb_scale = {FUDGE_2022}  (2022 pickle / FITS ratio)\n",
        file=sys.stderr,
    )

    # Same work as sharma2020_paper_tb.py; that module writes the PNG.
    rc = paper_tb.main(
        [
            "--config",
            args.config,
            "--flux-dir",
            str(args.flux_dir),
            "--nsig",
            str(args.nsig),
            "--out",
            str(args.out),
            *(["--reuse"] if args.reuse else []),
        ]
    )
    if rc:
        return rc

    # Show why 9.48 and F(ν) look alike but are not interchangeable.
    s_odot = paper_tb.load_s_odot(args.flux_dir)
    packed = __import__("numpy").load(REPO_ROOT / "data" / "quiet2015" / "fig4_paper_jy.npz")
    print()
    print(f"{'MHz':>5s}  {'F(ν)':>8s}  {'9.48':>8s}  {'peak MK':>8s}  {'caption':>8s}")
    for lab, ch, _ in list(fig4.MWA_TOP) + [("240", "187-188", None)]:
        hdr = paper_tb._header_from_npz(packed, ch)
        rec = scale_image(
            packed[f"{ch}_jy"],
            hdr,
            s_odot[lab] * 1e4,
            nsig=args.nsig,
            freq_hz=float(packed[f"{ch}_freq_hz"]),
        )
        cap = CAPTION_MK[lab]
        cap_s = f"{cap:8.2f}" if cap is not None else f"{'—':>8s}"
        print(
            f"{lab:>5s}  {rec['f_nu']:8.2f}  {FUDGE_2022:8.2f}  "
            f"{rec['tb_K'].max() / 1e6:8.3f}  {cap_s}"
        )
    print(
        "\nF(ν) is the stretch the 2020 paper computes. 9.48 is a frozen "
        "copy of a similar stretch from the 2022 cubes. Use F(ν)."
    )
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
