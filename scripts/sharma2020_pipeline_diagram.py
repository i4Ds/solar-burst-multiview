#!/usr/bin/env python3
"""Pipeline diagram for Sharma 2020 Figure 4: his work vs ours.

    python scripts/sharma2020_pipeline_diagram.py
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

from solarburst.config import REPO_ROOT

OUT = REPO_ROOT / "figures" / "sharma2020" / "fig4_pipeline.png"

C_ROHIT = "#e8e4dc"
C_OURS = "#d6e6f5"
C_FLUX = "#dcecc8"
C_EDGE = "#333333"


def box(ax, x, y, w, h, text, facecolor, *, weight="normal", size=9.5):
    p = FancyBboxPatch(
        (x - w / 2, y - h / 2),
        w,
        h,
        boxstyle="round,pad=0.012,rounding_size=0.08",
        facecolor=facecolor,
        edgecolor=C_EDGE,
        linewidth=1.1,
    )
    ax.add_patch(p)
    ax.text(
        x,
        y,
        text,
        ha="center",
        va="center",
        fontsize=size,
        fontweight=weight,
        color="#1a1a1a",
        linespacing=1.25,
    )
    return (x, y, w, h)


def arrow(ax, a, b):
    ax.add_patch(
        FancyArrowPatch(
            a,
            b,
            arrowstyle="-|>",
            mutation_scale=12,
            linewidth=1.2,
            color=C_EDGE,
            shrinkA=1,
            shrinkB=1,
        )
    )


def main() -> int:
    fig, ax = plt.subplots(figsize=(12.6, 9.4))
    ax.set_xlim(0, 12.6)
    ax.set_ylim(0, 9.4)
    ax.axis("off")
    ax.set_title(
        "Sharma & Oberoi 2020, Figure 4 — what actually ran",
        fontsize=14,
        pad=10,
        loc="left",
        fontweight="bold",
    )

    ax.text(6.3, 9.05, "Rohit, 2015  ·  we did not repeat this", fontsize=9, color="#555555", ha="center")
    c = box(ax, 3.4, 8.25, 3.8, 0.9, "Calibrator scan\n01:02 UT", C_ROHIT)
    g = box(ax, 9.2, 8.25, 3.8, 0.9, "Bandpass and gain solutions", C_ROHIT)
    arrow(ax, (c[0] + c[2] / 2, c[1]), (g[0] - g[2] / 2, g[1]))

    m = box(
        ax,
        6.3,
        6.85,
        5.8,
        1.1,
        "Solar visibilities  ·  03:39–03:44 UT\nCORRECTED_DATA already applied",
        C_ROHIT,
    )
    arrow(ax, (c[0], c[1] - c[3] / 2), (m[0] - 1.5, m[1] + m[3] / 2))
    arrow(ax, (g[0], g[1] - g[3] / 2), (m[0] + 1.5, m[1] + m[3] / 2))

    ax.text(3.15, 5.95, "His imaging", fontsize=9, color="#555555", ha="center")
    ax.text(9.45, 5.95, "Our imaging", fontsize=9, color="#555555", ha="center")
    h = box(
        ax,
        3.15,
        4.95,
        4.7,
        1.4,
        "CASA 5.3  classic clean\nSuperUniform, Hogbom, 8000 steps\n570 half-second maps",
        C_ROHIT,
        size=9,
    )
    o = box(
        ax,
        9.45,
        4.95,
        4.7,
        1.4,
        "CASA 6.6  tclean\n(this installation does not include classic clean)\nhalf-second maps on disk",
        C_OURS,
        size=9,
        weight="bold",
    )
    arrow(ax, (m[0] - 1.5, m[1] - m[3] / 2), (h[0], h[1] + h[3] / 2))
    arrow(ax, (m[0] + 1.5, m[1] - m[3] / 2), (o[0], o[1] + o[3] / 2))

    ax.text(
        6.3,
        3.85,
        "Brightness temperature  ·  applied to both sets of maps",
        fontsize=9,
        color="#555555",
        ha="center",
    )
    s = box(
        ax,
        6.3,
        2.95,
        7.2,
        1.05,
        "Whole-Sun flux from the shortest baselines\n+ Haslam 1982 sky at this pointing  (not the 2013 table)",
        C_FLUX,
        size=9,
    )
    arrow(ax, (h[0], h[1] - h[3] / 2), (s[0] - 1.6, s[1] + s[3] / 2))
    arrow(ax, (o[0], o[1] - o[3] / 2), (s[0] + 1.6, s[1] + s[3] / 2))

    f = box(
        ax,
        6.3,
        1.6,
        7.2,
        1.05,
        "Each map × Mohan stretch F(ν) at 5σ\nthen the time mean  →  million K",
        C_FLUX,
        size=9,
        weight="bold",
    )
    arrow(ax, (s[0], s[1] - s[3] / 2), (f[0], f[1] + f[3] / 2))
    fig4 = box(ax, 6.3, 0.55, 3.4, 0.65, "Figure 4", C_FLUX, weight="bold", size=11)
    arrow(ax, (f[0], f[1] - f[3] / 2), (fig4[0], fig4[1] + fig4[3] / 2))

    ax.text(
        6.3,
        0.08,
        "Not in this picture: P-AIRCARS, raw correlator files, the unpublished FEKO tile beam.",
        fontsize=8,
        color="#555555",
        ha="center",
    )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
