"""2x2 T_B maps (style of Sharma & Oberoi 2020) of the 2022 quiet Sun at 137 MHz:
4.7 min (one observation) and 13 min (three), each with the 2022 and the 2015 wsclean
settings (quiet_settings.sbatch). Plain wsclean images, no primary-beam correction:
compare the panels with each other, not with P-AIRCARS's pbcor values.

    python scripts/quiet_settings_compare.py data/flare20220930/quiet_long --out figures/flare20220930/quiet_long_settings
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle, Ellipse

sys.path.insert(0, str(Path(__file__).parent))
from uv_test_compare import RSUN, tb_hpc  # noqa: E402

PANELS = [("short_s2022", "4.7 min, 2022 imaging settings"), ("short_s2015", "4.7 min, 2015 imaging settings"),
          ("long_s2022", "13 min, 2022 imaging settings"), ("long_s2015", "13 min, 2015 imaging settings")]


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("dir", type=Path)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()

    fig, axs = plt.subplots(2, 2, figsize=(12, 10.5), layout="constrained")
    stats = {}
    for ax, (v, title) in zip(axs.flat, PANELS):
        tb, ext, nu, (bmaj, bmin, bpa) = tb_hpc(a.dir / f"{v}-image.fits")
        n = tb.shape[0]; cell = (ext[1] - ext[0]) / n
        ax1 = ext[0] + (np.arange(n) + 0.5) * cell
        X, Y = np.meshgrid(ax1, ax1); R = np.hypot(X, Y)
        sy, sx = np.unravel_index(np.nanargmax(tb), tb.shape)
        keep = np.hypot(X - X[sy, sx], Y - Y[sy, sx]) > 400
        med = float(np.nanmedian(tb[(R < 0.8 * RSUN) & keep]))
        stats[v] = dict(median_disk_MK_storm_excluded=med, peak_MK=float(np.nanmax(tb)), beam_arcsec=[bmaj, bmin])
        im = ax.imshow(np.where(tb > 0.2, tb, np.nan), origin="lower", extent=ext, cmap="jet", vmin=0, vmax=1.5)
        for r in (1, 2):
            ax.add_patch(Circle((0, 0), r * RSUN, fill=False, color="brown", lw=2))
        ax.add_patch(Ellipse((-2000, -2000), bmin, bmaj, angle=-bpa, fill=False, color="black"))
        ax.set_xlim(-2500, 2500); ax.set_ylim(-2500, 2500); ax.set_aspect("equal"); ax.grid(ls=":", color="grey")
        ax.set_xlabel("Solar X (arcsec)"); ax.set_ylabel("Solar Y (arcsec)")
        ax.set_title(f"{nu/1e6:.1f} MHz, {title}\nquiet disk median {med:.2f} MK (storm excluded), "
                     f"peak {np.nanmax(tb):.1f} MK", fontsize=10)
    fig.colorbar(im, ax=axs, shrink=0.6, label="T_B (MK)")
    fig.suptitle("Quiet Sun 2022-09-30 03:20–03:33, PKS0408-65 + self-cal; colour scale saturates on the storm")
    a.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(f"{a.out}.png", dpi=110)
    json.dump(stats, open(f"{a.out}.json", "w"), indent=1)
    print(json.dumps(stats, indent=1))


if __name__ == "__main__":
    main()
