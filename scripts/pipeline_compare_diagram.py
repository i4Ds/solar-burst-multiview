#!/usr/bin/env python3
"""Generic comparison of imaging pipelines, same drawing style as Figure 4.

Each entry in PIPELINES is one column. Add a later method by appending a
dict with the same four stage keys. Do not draw an empty column.

    python scripts/pipeline_compare_diagram.py
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
C_COMPARE = "#dcecc8"

# Stage order is the row axis. Every pipeline must fill every stage.
STAGES = ("Calibration", "Imaging", "Flux scale", "Product")

PIPELINES = [
    {
        "name": "Sharma & Oberoi 2020",
        "cite": "published quiet-Sun method",
        "color": "#e8e4dc",
        "stages": {
            "Calibration": (
                "Phase-only CASA bandpass on a\n"
                "compact calibrator  (B Jones, |g| = 1).\n"
                "Apply to the Sun. No self-calibration."
            ),
            "Imaging": (
                "CASA classic clean\n"
                "SuperUniform, Hogbom, 8000 iterations\n"
                "half-second snapshots"
            ),
            "Flux scale": (
                "Whole-Sun flux from the shortest baselines\n"
                "+ Haslam 1982 sky at this pointing\n"
                "Oberoi, Sharma & Rogers 2017"
            ),
            "Product": (
                "Each map × Mohan F(ν) at 5σ\n"
                "then the time mean  →  brightness\n"
                "temperature, MK"
            ),
        },
        "compare": (
            "Whole-Sun flux from the shortest baselines\n"
            "+ Haslam 1982 sky at this pointing\n"
            "(Oberoi, Sharma & Rogers 2017).\n"
            "Each map × Mohan F(ν) at 5σ,\n"
            "then the time mean."
        ),
    },
    {
        "name": "P-AIRCARS",
        "cite": "Kansabanik et al. 2022–2025",
        "color": "#d6e6f5",
        "stages": {
            "Calibration": (
                "Calibrator bandpass and flux from a\n"
                "sky model. Apply to the Sun.\n"
                "Intensity self-calibration (Mondal et al.\n"
                "2019); this step can be turned off."
            ),
            "Imaging": (
                "WSClean, Briggs robust 0, multiscale\n"
                "primary-beam correction\n"
                "helioprojective, solar north"
            ),
            "Flux scale": (
                "Absolute flux from the calibrator sky model.\n"
                "Primary-beam-corrected Jy/beam.\n"
                "Not the Oberoi short-baseline flux."
            ),
            "Product": (
                "Stokes IQUV cubes, Jy/beam,\n"
                "at the chosen time and frequency\n"
                "resolution"
            ),
        },
        "compare": (
            "Primary-beam-corrected Jy/beam\n"
            "from the calibrator sky model.\n"
            "Each map × Mohan F(ν) at 5σ\n"
            "→ MK.\n"
            "This conversion is not a P-AIRCARS step."
        ),
    },
]


def box(ax, x, y, w, h, text, facecolor, *, weight="normal", size=8.5, linestyle="solid"):
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


def down(a, b):
    return (a[0], a[1] - a[3] / 2), (b[0], b[1] + b[3] / 2)


def main() -> int:
    n = len(PIPELINES)
    if n < 1:
        raise SystemExit("PIPELINES is empty")
    for p in PIPELINES:
        missing = [s for s in STAGES if s not in p["stages"]]
        if missing:
            raise SystemExit(f"{p['name']} missing stages: {missing}")
        if "compare" not in p:
            raise SystemExit(f"{p['name']} missing compare text")

    left = 1.15
    right = 0.35
    gap = 0.38
    fig_h = 13.8
    col_w = 5.15
    fig_w = left + right + n * col_w + (n - 1) * gap
    xs = [left + col_w / 2 + i * (col_w + gap) for i in range(n)]
    box_w = col_w - 0.22
    span_w = min(fig_w - left - right, n * col_w + (n - 1) * gap)

    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    ax.set_xlim(0, fig_w)
    ax.set_ylim(0, fig_h)
    ax.axis("off")
    ax.set_title("Imaging pipelines", fontsize=14, pad=10, loc="left", fontweight="bold")

    mid = (xs[0] + xs[-1]) / 2
    src = box(
        ax,
        mid,
        12.55,
        span_w,
        0.95,
        "Uncalibrated MWA visibilities  ·  Sun scan and a compact calibrator",
        C_INPUT,
        size=9,
        weight="bold",
    )

    y_head = 11.55
    for x, p in zip(xs, PIPELINES):
        ax.text(x, y_head, p["name"], fontsize=11, fontweight="bold", ha="center", va="center")
        ax.text(x, y_head - 0.32, p["cite"], fontsize=8.5, color="#555555", ha="center", va="center")

    # Row centres: calibration, imaging, flux, product.
    ys = (10.05, 8.05, 6.10, 4.25)
    heights = (1.55, 1.55, 1.40, 1.25)
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
                    size=8.4,
                    weight="bold" if stage == "Product" else "normal",
                )
            )
        cells.append(col)

    for i, stage in enumerate(STAGES):
        ax.text(0.28, ys[i], stage, fontsize=8, color="#555555", rotation=90, va="center")

    for col, x in zip(cells, xs):
        arrow(ax, (src[0] + (x - mid) * 0.35, src[1] - src[3] / 2), (x, col[0][1] + col[0][3] / 2))
        for a, b in zip(col, col[1:]):
            arrow(ax, *down(a, b))

    note = box(
        ax,
        mid,
        1.85,
        span_w,
        2.15,
        "",
        C_COMPARE,
        linestyle="dashed",
    )
    ax.text(
        mid,
        2.68,
        "Comparison  ·  brightness temperature, MK",
        ha="center",
        va="center",
        fontsize=9,
        fontweight="bold",
        color="#1a1a1a",
    )
    for x, p in zip(xs, PIPELINES):
        text = p["compare"]
        ax.text(
            x,
            1.55,
            text,
            ha="center",
            va="center",
            fontsize=8.2,
            color="#1a1a1a",
            linespacing=1.25,
        )
    ax.text(0.28, 1.85, "Comparison", fontsize=8, color="#555555", rotation=90, va="center")
    for col in cells:
        arrow(ax, *down(col[-1], note), linestyle="dashed")

    ax.text(
        mid,
        0.38,
        "P-AIRCARS polarisation calibration is off by default. "
        "The Sharma & Oberoi 2020 column is the published method, not a remake.",
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
