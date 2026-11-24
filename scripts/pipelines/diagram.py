#!/usr/bin/env python3
"""Three quiet-Sun imaging pipelines, one column each.

Same visibilities at the top. Each column is a complete path from
calibration to product. Rebuild:

    python scripts/pipelines/diagram.py
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

from solarburst.config import REPO_ROOT

OUT = REPO_ROOT / "figures" / "pipelines.png"

C_EDGE = "#333333"
C_INPUT = "#f3e2c4"

STAGES = ("Calibration", "Imaging", "Flux scale", "Product")

PIPELINES = [
    {
        "name": "Sharma & Oberoi 2020",
        "cite": "published quiet-Sun method, ApJ 903, 126",
        "color": "#e8e4dc",
        "stages": {
            "Calibration": (
                "Phase-only CASA bandpass on a\n"
                "compact calibrator  (B Jones, |g| = 1).\n"
                "Apply to the Sun."
            ),
            "Imaging": (
                "CASA 5.3 classic clean\n"
                "SuperUniform, Hogbom, 8000 iterations\n"
                "half-second snapshots, 1024² × 50″"
            ),
            "Flux scale": (
                "Whole-Sun flux from the shortest baselines\n"
                "and Haslam 1982 sky at this pointing\n"
                "Oberoi, Sharma & Rogers 2017"
            ),
            "Product": (
                "Each map × Mohan F(ν) at 5σ\n"
                "then the time mean\n"
                "brightness temperature, MK"
            ),
        },
    },
    {
        "name": "CASA remake",
        "cite": "this work, same SuperUniform numbers",
        "color": "#d6e6f5",
        "stages": {
            "Calibration": (
                "The same phase-only bandpass tables\n"
                "applied with CASA applycal\n"
                "(applymode=calonly, calwt=False)."
            ),
            "Imaging": (
                "CASA 6.6 tclean\n"
                "SuperUniform, Hogbom, 8000 iterations\n"
                "half-second snapshots, 1024² × 50″"
            ),
            "Flux scale": (
                "Whole-Sun flux from the shortest baselines\n"
                "and Haslam 1982 sky at this pointing\n"
                "same Oberoi 2017 formula"
            ),
            "Product": (
                "Each map × Mohan F(ν) at 5σ\n"
                "then the time mean\n"
                "brightness temperature, MK"
            ),
        },
    },
    {
        "name": "P-AIRCARS",
        "cite": "Kansabanik et al. 2022–2025",
        "color": "#cfe8d5",
        "stages": {
            "Calibration": (
                "Calibrator bandpass and flux from a\n"
                "sky model. Apply to the Sun.\n"
                "Intensity self-calibration optional."
            ),
            "Imaging": (
                "WSClean, Briggs robust 0, multiscale\n"
                "primary-beam correction\n"
                "helioprojective, solar north"
            ),
            "Flux scale": (
                "Absolute flux from the calibrator\n"
                "sky model. Primary-beam-corrected\n"
                "Jy/beam."
            ),
            "Product": (
                "Stokes I cubes, Jy/beam,\n"
                "at the chosen time and frequency.\n"
                "T_B via Rayleigh–Jeans for plots."
            ),
        },
    },
]


def box(ax, x, y, w, h, text, facecolor, *, weight="normal", size=8.3):
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


def down(a, b):
    return (a[0], a[1] - a[3] / 2), (b[0], b[1] + b[3] / 2)


def main() -> int:
    n = len(PIPELINES)
    left, right, gap = 1.15, 0.35, 0.32
    fig_h = 12.4
    col_w = 5.05
    fig_w = left + right + n * col_w + (n - 1) * gap
    xs = [left + col_w / 2 + i * (col_w + gap) for i in range(n)]
    box_w = col_w - 0.20
    span_w = n * col_w + (n - 1) * gap

    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    ax.set_xlim(0, fig_w)
    ax.set_ylim(0, fig_h)
    ax.axis("off")
    ax.set_title(
        "Three quiet-Sun imaging pipelines",
        fontsize=14,
        pad=10,
        loc="left",
        fontweight="bold",
    )

    mid = (xs[0] + xs[-1]) / 2
    src = box(
        ax,
        mid,
        11.55,
        span_w,
        0.85,
        "Uncalibrated MWA visibilities  ·  Sun scan and a compact calibrator",
        C_INPUT,
        size=9,
        weight="bold",
    )

    y_head = 10.55
    for x, p in zip(xs, PIPELINES):
        ax.text(x, y_head, p["name"], fontsize=11, fontweight="bold", ha="center", va="center")
        ax.text(x, y_head - 0.32, p["cite"], fontsize=8.2, color="#555555", ha="center", va="center")

    ys = (8.95, 6.85, 4.80, 2.70)
    heights = (1.50, 1.50, 1.45, 1.45)
    cells: list[list[tuple]] = []
    for x, p in zip(xs, PIPELINES):
        col = []
        for stage, y, h in zip(STAGES, ys, heights):
            col.append(
                box(
                    ax,
                    x,
                    y,
                    box_w,
                    h,
                    p["stages"][stage],
                    p["color"],
                    size=8.2,
                    weight="bold" if stage == "Product" else "normal",
                )
            )
        cells.append(col)

    for i, stage in enumerate(STAGES):
        ax.text(0.28, ys[i], stage, fontsize=8, color="#555555", rotation=90, va="center")

    for col, x in zip(cells, xs):
        arrow(ax, (src[0] + (x - mid) * 0.28, src[1] - src[3] / 2), (x, col[0][1] + col[0][3] / 2))
        for a, b in zip(col, col[1:]):
            arrow(ax, *down(a, b))

    ax.text(
        mid,
        0.55,
        "3 December 2015, 03:39–03:44 UT  ·  108, 162, 217, 240 MHz  ·  "
        "each column is a complete path",
        fontsize=8.5,
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
