#!/usr/bin/env python3
"""Pipeline diagram for Sharma 2020 Figure 4.

Three columns: Rohit's published maps, our remake of his visibilities, and
the planned start from uncalibrated visibilities through P-AIRCARS.

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
C_PLAN = "#f3e2c4"
C_FLUX = "#dcecc8"
C_EDGE = "#333333"


def box(ax, x, y, w, h, text, facecolor, *, weight="normal", size=9.0, linestyle="solid"):
    p = FancyBboxPatch(
        (x - w / 2, y - h / 2),
        w,
        h,
        boxstyle="round,pad=0.012,rounding_size=0.08",
        facecolor=facecolor,
        edgecolor=C_EDGE,
        linewidth=1.1,
        linestyle=linestyle,
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


def arrow(ax, a, b, *, linestyle="solid"):
    ax.add_patch(
        FancyArrowPatch(
            a,
            b,
            arrowstyle="-|>",
            mutation_scale=12,
            linewidth=1.2,
            color=C_EDGE,
            linestyle=linestyle,
            shrinkA=1,
            shrinkB=1,
        )
    )


def main() -> int:
    fig, ax = plt.subplots(figsize=(14.8, 10.2))
    ax.set_xlim(0, 14.8)
    ax.set_ylim(0, 10.2)
    ax.axis("off")
    ax.set_title(
        "Sharma & Oberoi 2020, Figure 4",
        fontsize=14,
        pad=10,
        loc="left",
        fontweight="bold",
    )

    ax.text(2.5, 9.65, "Rohit, 2015", fontsize=9, color="#555555", ha="center")
    ax.text(7.4, 9.65, "Our remake of his visibilities", fontsize=9, color="#555555", ha="center")
    ax.text(12.2, 9.65, "From uncalibrated visibilities  ·  planned", fontsize=9, color="#555555", ha="center")

    r_vis = box(
        ax,
        2.5,
        8.55,
        4.4,
        1.25,
        "Cen A solutions already applied\nsolar visibilities 03:39–03:44 UT\nCORRECTED_DATA",
        C_ROHIT,
        size=8.5,
    )
    o_vis = box(
        ax,
        7.4,
        8.55,
        4.4,
        1.25,
        "The same visibilities\nCen A solutions as Rohit applied them",
        C_OURS,
        size=8.5,
        weight="bold",
    )
    p_vis = box(
        ax,
        12.2,
        8.55,
        4.4,
        1.25,
        "Archive conversion, uncalibrated\nSun 0.5 s, Cen A 4 s\n108, 162, 217, 240 MHz",
        C_PLAN,
        size=8.5,
        linestyle="dashed",
    )
    arrow(ax, (r_vis[0] + r_vis[2] / 2, r_vis[1]), (o_vis[0] - o_vis[2] / 2, o_vis[1]))

    r_im = box(
        ax,
        2.5,
        6.55,
        4.4,
        1.55,
        "CASA 5.3  classic clean\nSuperUniform, Hogbom, 8000 steps\n570 half-second maps",
        C_ROHIT,
        size=8.5,
    )
    o_im = box(
        ax,
        7.4,
        6.55,
        4.4,
        1.55,
        "CASA 6.6  tclean\n(this installation does not include\nclassic clean)  570 maps on disk",
        C_OURS,
        size=8.5,
        weight="bold",
    )
    p_im = box(
        ax,
        12.2,
        6.55,
        4.4,
        1.55,
        "P-AIRCARS  (planned, not run)\nsolve Cen A, apply to the Sun\nimage the four bands",
        C_PLAN,
        size=8.5,
        weight="bold",
        linestyle="dashed",
    )
    arrow(ax, (r_vis[0], r_vis[1] - r_vis[3] / 2), (r_im[0], r_im[1] + r_im[3] / 2))
    arrow(ax, (o_vis[0], o_vis[1] - o_vis[3] / 2), (o_im[0], o_im[1] + o_im[3] / 2))
    arrow(
        ax,
        (p_vis[0], p_vis[1] - p_vis[3] / 2),
        (p_im[0], p_im[1] + p_im[3] / 2),
        linestyle="dashed",
    )

    ax.text(
        7.4,
        5.35,
        "Brightness temperature  ·  Oberoi et al. 2017 and Mohan & Oberoi 2017",
        fontsize=9,
        color="#555555",
        ha="center",
    )
    s = box(
        ax,
        7.4,
        4.35,
        8.6,
        1.05,
        "Whole-Sun flux from the shortest baselines\n+ Haslam 1982 sky at this pointing  (not the 2013 table)",
        C_FLUX,
        size=9,
    )
    arrow(ax, (r_im[0], r_im[1] - r_im[3] / 2), (s[0] - 2.4, s[1] + s[3] / 2))
    arrow(ax, (o_im[0], o_im[1] - o_im[3] / 2), (s[0], s[1] + s[3] / 2))
    arrow(
        ax,
        (p_im[0], p_im[1] - p_im[3] / 2),
        (s[0] + 2.4, s[1] + s[3] / 2),
        linestyle="dashed",
    )

    f = box(
        ax,
        7.4,
        2.75,
        8.6,
        1.05,
        "Each map × Mohan F(ν) at 5σ\nthen the time mean  →  brightness temperature, million K",
        C_FLUX,
        size=9,
        weight="bold",
    )
    arrow(ax, (s[0], s[1] - s[3] / 2), (f[0], f[1] + f[3] / 2))
    fig4 = box(ax, 7.4, 1.35, 3.6, 0.7, "Figure 4", C_FLUX, weight="bold", size=11)
    arrow(ax, (f[0], f[1] - f[3] / 2), (fig4[0], fig4[1] + fig4[3] / 2))

    ax.text(
        7.4,
        0.45,
        "Dashed boxes are planned and have not been run. The unpublished FEKO tile beam is not shown.",
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
