#!/usr/bin/env python3
"""Print the last CASA clean() that wrote Rohit's published FITS.

    python scripts/sharma2020_fits_history.py
    python scripts/sharma2020_fits_history.py path/to/one.FITS
"""

from __future__ import annotations

import argparse
from pathlib import Path

from solarburst.config import load, local_path
from solarburst.sharma2020 import BANDS, last_clean_from_history, list_fits


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("fits", nargs="*", type=Path)
    args = p.parse_args(argv)
    paths = list(args.fits)
    if not paths:
        cfg = load("sharma2022")
        fitsdir = local_path(cfg, cfg["remote"]["paths"]["fits"])
        for lab, ch, _ in BANDS:
            files = list_fits(fitsdir, ch)
            paths.append(files[0])
            print(f"{lab} MHz  {len(files)} frames  first={files[0].name}")
    for path in paths:
        rec = last_clean_from_history(path)
        print(f"\n{path.name}")
        for k, v in rec.items():
            print(f"  {k:14s} {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
