"""Baseline lengths (in wavelengths) of an MS: unique cross-correlation baselines
with any unflagged data, projected at the middle time step.

    python3 uv_hist.py <ms> <out.npz>
"""
import sys

import numpy as np
from casacore.tables import table

ms, out = sys.argv[1], sys.argv[2]
t = table(ms, ack=False)
times = np.unique(t.getcol("TIME"))
mid = t.query(f"TIME == {times[len(times)//2]!r} && ANTENNA1 != ANTENNA2")
uvw, flag = mid.getcol("UVW"), mid.getcol("FLAG")
nu = table(f"{ms}/SPECTRAL_WINDOW", ack=False).getcol("CHAN_FREQ").mean()
ok = ~flag.all(axis=(1, 2))
uvl = np.hypot(uvw[:, 0], uvw[:, 1]) * nu / 299792458.0
uvl = uvl[ok]
edges = np.array([0, 10, 20, 40, 60, 100, 150, 200, 300, 500, 1000, 2000, 5000])
h, _ = np.histogram(uvl, edges)
np.savez(out, uvl=uvl, nu=nu, edges=edges, hist=h)
print(f"{ms}: {nu/1e6:.2f} MHz, {ok.sum()} unflagged baselines of {len(ok)}, shortest {uvl.min():.1f} lambda")
for a, b, n in zip(edges[:-1], edges[1:], h):
    print(f"  {a:5.0f}-{b:5.0f} lambda: {n:5d}")
