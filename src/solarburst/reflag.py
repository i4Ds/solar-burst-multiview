"""Replace AOFlagger flags in an ASVO solar MS by dead-tile and missing-data flags.

AOFlagger treats solar bursts as RFI: on 2022-09-30 the 4 s steps of a type III
burst at 143 MHz were 95–98 % flagged, against a floor of 35 % from dead tiles.
This writes a copy whose FLAG is only

* every baseline of an antenna that is flagged in all its cross rows (dead tile)
* samples whose DATA is exactly zero or not finite

Birli also zeroes the weights of flagged samples, and wsclean skips zero
weights whatever FLAG says. Unflagged samples therefore keep their weight if it
is positive and otherwise get the observation's full weight (the maximum per
correlation), which is what a sample with no raw data flagged receives.

    python reflag.py IN.ms OUT.ms

Inside the calculon container (python-casacore). No package imports, so it can
run as a plain file.
"""

from __future__ import annotations

import argparse

import numpy as np


def reflag(src: str, dst: str) -> None:
    from casacore.tables import table

    with table(src, ack=False) as t:
        t.copy(dst, deep=True)
    with table(dst, readonly=False, ack=False) as t:
        a1, a2 = t.getcol("ANTENNA1"), t.getcol("ANTENNA2")
        flag = t.getcol("FLAG")
        cross = a1 != a2
        nant = int(max(a1.max(), a2.max())) + 1
        rows_all_flagged = flag.all(axis=(1, 2))
        dead = [a for a in range(nant)
                if (sel := cross & ((a1 == a) | (a2 == a))).any() and rows_all_flagged[sel].all()]
        data = t.getcol("DATA")
        new = (~np.isfinite(data)) | (data == 0)
        new |= np.isin(a1, dead)[:, None, None] | np.isin(a2, dead)[:, None, None]
        t.putcol("FLAG", new)
        t.putcol("FLAG_ROW", new.all(axis=(1, 2)))
        if "WEIGHT_SPECTRUM" in t.colnames():
            w = t.getcol("WEIGHT_SPECTRUM")
            full = w.max(axis=(0, 1))
            w = np.where(new, 0.0, np.where(w > 0, w, full)).astype(w.dtype)
            t.putcol("WEIGHT_SPECTRUM", w)
        w = t.getcol("WEIGHT")  # (row, corr)
        full = w.max(axis=0)
        row_flag = new.all(axis=1)
        t.putcol("WEIGHT", np.where(row_flag, 0.0, np.where(w > 0, w, full)).astype(w.dtype))
    print(f"{dst}: {len(dead)} dead antennas {dead}; "
          f"flagged {flag[cross].mean():.2f} -> {new[cross].mean():.2f} of cross samples")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("src")
    p.add_argument("dst")
    args = p.parse_args()
    reflag(args.src, args.dst)


if __name__ == "__main__":
    main()
