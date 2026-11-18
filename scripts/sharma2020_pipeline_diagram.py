#!/usr/bin/env python3
"""Pipeline diagram for Sharma 2020 Figure 4.

P-AIRCARS is the calibration step from uncalibrated archive visibilities.
It should write the same CORRECTED_DATA as Rohit's measurement sets.
CASA imaging follows on every path; P-AIRCARS does not replace it.

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


def arrow(ax, a, b, *, linestyle="solid", style="-|>"):
    ax.add_patch(
        FancyArrowPatch(
            a,
            b,
            arrowstyle=style,
            mutation_scale=12,
            linewidth=1.2,
            color=C_EDGE,
            linestyle=linestyle,
            shrinkA=1,
            shrinkB=1,
        )
    )


def down(a, b):
    return (a[0], a[1] - a[3] / 2), (b[0], b[1] + b[3] / 2)


def right(a, b):
    return (a[0] + a[2] / 2, a[1]), (b[0] - b[2] / 2, b[1])


def left(a, b):
    return (a[0] - a[2] / 2, a[1]), (b[0] + b[2] / 2, b[1])


def main() -> int:
    fig, ax = plt.subplots(figsize=(15.6, 12.0))
    ax.set_xlim(0, 15.6)
    ax.set_ylim(0, 12.0)
    ax.axis("off")
    ax.set_title(
        "Sharma & Oberoi 2020, Figure 4",
        fontsize=14,
        pad=10,
        loc="left",
        fontweight="bold",
    )

    ax.text(2.55, 11.45, "Rohit, 2015", fontsize=9, color="#555555", ha="center")
    ax.text(7.7, 11.45, "Our remake of his visibilities", fontsize=9, color="#555555", ha="center")
    ax.text(12.85, 11.45, "From uncalibrated visibilities", fontsize=9, color="#555555", ha="center")

    ax.text(0.28, 8.55, "Calibration", fontsize=8, color="#555555", rotation=90, va="center")
    ax.text(0.28, 5.95, "Imaging", fontsize=8, color="#555555", rotation=90, va="center")

    p_raw = box(
        ax,
        12.85,
        10.45,
        4.55,
        1.15,
        "Archive conversion, uncalibrated\nSun 0.5 s, Cen A 4 s\n108, 162, 217, 240 MHz",
        C_PLAN,
        size=8.5,
    )
    p_cal = box(
        ax,
        12.85,
        8.55,
        4.55,
        1.45,
        "P-AIRCARS calibration\nsolve Cen A, apply to the Sun\nwrites CORRECTED_DATA",
        C_PLAN,
        size=8.5,
        weight="bold",
    )
    r_vis = box(
        ax,
        2.55,
        8.55,
        4.55,
        1.45,
        "Cen A solutions already applied\nsolar visibilities 03:39–03:44 UT\nCORRECTED_DATA",
        C_ROHIT,
        size=8.5,
    )
    o_vis = box(
        ax,
        7.7,
        8.55,
        4.55,
        1.45,
        "The same visibilities\nCen A solutions as Rohit applied them",
        C_OURS,
        size=8.5,
        weight="bold",
    )
    arrow(ax, *down(p_raw, p_cal))
    arrow(ax, *right(r_vis, o_vis))
    arrow(ax, *left(p_cal, o_vis), linestyle="dashed", style="<|-|>")
    ax.text(
        10.28,
        9.38,
        "should match",
        fontsize=8,
        color="#555555",
        ha="center",
    )

    r_im = box(
        ax,
        2.55,
        5.95,
        4.55,
        1.55,
        "CASA 5.3  classic clean\nSuperUniform, Hogbom, 8000 steps\n570 half-second maps",
        C_ROHIT,
        size=8.5,
    )
    o_im = box(
        ax,
        7.7,
        5.95,
        4.55,
        1.55,
        "CASA 6.6  tclean\n(this installation does not include\nclassic clean)  570 maps on disk",
        C_OURS,
        size=8.5,
        weight="bold",
    )
    p_im = box(
        ax,
        12.85,
        5.95,
        4.55,
        1.55,
        "CASA 6.6  tclean\nsame SuperUniform, Hogbom, 8000 steps\nas the remake of his visibilities",
        C_PLAN,
        size=8.5,
        weight="bold",
        linestyle="dashed",
    )
    arrow(ax, *down(r_vis, r_im))
    arrow(ax, *down(o_vis, o_im))
    arrow(ax, *down(p_cal, p_im), linestyle="dashed")

    ax.text(
        7.7,
        4.72,
        "Brightness temperature  ·  Oberoi et al. 2017 and Mohan & Oberoi 2017",
        fontsize=9,
        color="#555555",
        ha="center",
    )
    s = box(
        ax,
        7.7,
        3.78,
        8.8,
        1.05,
        "Whole-Sun flux from the shortest baselines\n+ Haslam 1982 sky at this pointing  (not the 2013 table)",
        C_FLUX,
        size=9,
    )
    arrow(ax, (r_im[0], r_im[1] - r_im[3] / 2), (s[0] - 2.5, s[1] + s[3] / 2))
    arrow(ax, (o_im[0], o_im[1] - o_im[3] / 2), (s[0], s[1] + s[3] / 2))
    arrow(
        ax,
        (p_im[0], p_im[1] - p_im[3] / 2),
        (s[0] + 2.5, s[1] + s[3] / 2),
        linestyle="dashed",
    )

    f = box(
        ax,
        7.7,
        2.22,
        8.8,
        1.05,
        "Each map × Mohan F(ν) at 5σ\nthen the time mean  →  brightness temperature, million K",
        C_FLUX,
        size=9,
        weight="bold",
    )
    arrow(ax, *down(s, f))
    fig4 = box(ax, 7.7, 0.95, 3.6, 0.7, "Figure 4", C_FLUX, weight="bold", size=11)
    arrow(ax, *down(f, fig4))

    ax.text(
        7.7,
        0.28,
        "P-AIRCARS writes CORRECTED_DATA; it does not replace CASA imaging. "
        "Dashed CASA is that path, not yet in the comparison figures. "
        "The unpublished FEKO tile beam is not shown.",
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
