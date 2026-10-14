"""Flag baselines of an MS so that its short-baseline counts match another layout.

    python3 uv_thin.py <ms> <reference_uv.npz> [--below 200] [--seed 1]

<reference_uv.npz> comes from uv_hist.py (e.g. the 2022 Phase II Extended observation).
In every histogram bin below --below wavelengths, a random subset of this MS's
baselines is kept so that the count equals the reference count. All rows of the
other baselines in those bins are flagged in place. Longer baselines are untouched.
Baseline lengths are taken at the middle time step, as in uv_hist.py.
"""
import argparse

import numpy as np
from casacore.tables import table

p = argparse.ArgumentParser()
p.add_argument("ms")
p.add_argument("ref")
p.add_argument("--below", type=float, default=200.0)
p.add_argument("--seed", type=int, default=1)
a = p.parse_args()

ref = np.load(a.ref)
edges, href = ref["edges"], ref["hist"]
rng = np.random.default_rng(a.seed)
t = table(a.ms, readonly=False, ack=False)
times = np.unique(t.getcol("TIME"))
mid = t.query(f"TIME == {times[len(times)//2]!r} && ANTENNA1 != ANTENNA2")
a1, a2, uvw, flag = mid.getcol("ANTENNA1"), mid.getcol("ANTENNA2"), mid.getcol("UVW"), mid.getcol("FLAG")
nu = table(f"{a.ms}/SPECTRAL_WINDOW", ack=False).getcol("CHAN_FREQ").mean()
uvl = np.hypot(uvw[:, 0], uvw[:, 1]) * nu / 299792458.0
ok = ~flag.all(axis=(1, 2))
drop = set()
for lo, hi, nref in zip(edges[:-1], edges[1:], href):
    if lo >= a.below:
        break
    idx = np.flatnonzero(ok & (uvl >= lo) & (uvl < hi))
    if idx.size > nref:
        gone = rng.choice(idx, idx.size - nref, replace=False)
        drop.update(zip(a1[gone].tolist(), a2[gone].tolist()))
    print(f"  {lo:5.0f}-{hi:5.0f} lambda: {idx.size:5d} -> {min(idx.size, nref):5d}")
A1, A2 = t.getcol("ANTENNA1"), t.getcol("ANTENNA2")
rows = np.flatnonzero([(x, y) in drop for x, y in zip(A1.tolist(), A2.tolist())])
f = t.getcol("FLAG")
f[rows] = True
t.putcol("FLAG", f)
t.close()
print(f"{a.ms}: flagged {len(drop)} baselines ({rows.size} rows)")
