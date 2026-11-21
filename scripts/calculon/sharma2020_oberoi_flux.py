#!/usr/bin/env python3
"""Oberoi 2017 S_odot from one quiet-scan MS. Runs in mwa-demo or paircars.

    python3 sharma2020_oberoi_flux.py MS OUT.json [--column DATA]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow `~/mwa/sharma2020/solarburst` or a repo checkout.
_HERE = Path(__file__).resolve().parent
for root in (_HERE, _HERE.parents[1] / "src"):
    if (root / "solarburst" / "oberoi2017.py").exists():
        sys.path.insert(0, str(root))
        break

from solarburst.oberoi2017 import measure_r_n, write_json  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("ms")
    p.add_argument("out")
    p.add_argument("--column", default=None)
    p.add_argument("--t-b-sky-from-table", action="store_true")
    p.add_argument("--use-flags", action="store_true")
    p.add_argument(
        "--sky",
        choices=("table1", "haslam"),
        default="table1",
        help="table1 = 2013 pointing (MS-only). haslam = this LST; needs the "
        "Haslam 1982 map on the machine. Laptop path: scripts/sharma2020_haslam_tsky.py",
    )
    args = p.parse_args(argv)
    result = measure_r_n(
        args.ms,
        column=args.column,
        t_b_sky_from_table=args.t_b_sky_from_table,
        use_flags=args.use_flags,
    )
    if args.sky == "haslam":
        from solarburst.oberoi2017 import apply_sky_terms, sky_terms_haslam

        sky = sky_terms_haslam(result["freq_mhz"])
        result = apply_sky_terms(result, sky)
    write_json(result, args.out)
    keys = (
        "ms", "column", "freq_mhz", "tile_source", "tiles",
        "n_auto_rows", "r_N", "t_odot_p_K", "s_odot_sfu",
        "t_sky_source", "note",
    )
    print(json.dumps({k: result[k] for k in keys}, indent=2))
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
