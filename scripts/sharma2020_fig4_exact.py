#!/usr/bin/env python3
"""Front door for Sharma & Oberoi 2020 Figure 4.

Runs ``scripts/sharma2020_pipeline.py``: Rohit's CASA 0.5 s FITS, Oberoi
2017 S_⊙, Mohan 2017 F(ν) on each frame, time-mean T_B. No 9.48.

    python scripts/sharma2020_fig4_exact.py
    python scripts/sharma2020_fig4_exact.py --reuse
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

if __name__ == "__main__":
    target = Path(__file__).with_name("sharma2020_pipeline.py")
    sys.argv = [str(target), *sys.argv[1:]]
    runpy.run_path(str(target), run_name="__main__")
