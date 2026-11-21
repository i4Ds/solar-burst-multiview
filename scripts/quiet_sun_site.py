#!/usr/bin/env python3
"""Build the quiet-Sun comparison site from the 2013–2015 noon catalogue.

Writes static HTML under site/quiet-sun/. Published as the private
i4Ds/mwa-quiet-sun repo. A day is mapped only when a figure already
exists on disk. Does not invent maps.
"""

from __future__ import annotations

import csv
import html
import shutil
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "configs/quiet/quiet_noon_2013_2015.csv"
SITE = ROOT / "site/quiet-sun"
MEDIA = SITE / "media"
FIG = ROOT / "figures"

# Sharma & Oberoi 2020 Fig. 4: not the noon pick that day.
FIG4_OBSID = "1133149192"
FIG4_NOON = "1133149792"
FIG4_START = "2015-12-03T03:39:44"

# Days with work already started. Status is only what we can show.
# Figure 4 is 1133149192 (03:39 UT), not the noon pick 1133149792 (03:49 UT).
WORK = {
    "1133236216": "waiting",  # 4 Dec 2015: CASA frames exist, mean T_B running
    "1111376776": "waiting",  # 26 Mar 2015: ASVO download submitted
}

FONT = (
    "https://fonts.googleapis.com/css2?"
    "family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&"
    "family=Source+Sans+3:wght@400;500;600&display=swap"
)


def cal_id(raw: str) -> str:
    if not raw:
        return ""
    return str(int(float(raw)))


def load_days() -> list[dict]:
    rows = []
    with CSV_PATH.open() as f:
        for r in csv.DictReader(f):
            start = r["starttime_utc"].replace(".000Z", "").replace("Z", "")
            date = start[:10]
            rows.append(
                {
                    "obsid": r["obs_id"],
                    "date": date,
                    "start": start,
                    "duration_s": int(float(r["duration"])),
                    "obsname": r["obsname"],
                    "alt": float(r["sun_alt"]),
                    "ha": float(r["ha_h"]),
                    "cal_obsid": cal_id(r["cal_obs_id"]),
                    "cal_name": r["cal_name"] or "",
                    "dt_cal": float(r["cal_dt_h"]) if r["cal_dt_h"] else None,
                    "year": date[:4],
                    "status": WORK.get(r["obs_id"], "none"),
                    "cal_within_24h": bool(
                        r["cal_dt_h"] and abs(float(r["cal_dt_h"])) <= 24.0
                    ),
                }
            )
    return rows


def e(s: object) -> str:
    return html.escape(str(s), quote=True)


def fmt_date(iso: str) -> str:
    return datetime.strptime(iso, "%Y-%m-%d").strftime("%-d %B %Y")


def fmt_time(iso: str) -> str:
    return iso.replace("T", " ") + " UT"


def head(title: str, *, root: str = ".") -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="{FONT}" rel="stylesheet">
<link rel="stylesheet" href="{root}/css/site.css">
</head>
<body>
"""


def nav(*, root: str = ".", current: str = "") -> str:
    def item(href: str, label: str, key: str) -> str:
        if current == key:
            return f"<strong>{label}</strong>"
        return f'<a href="{root}/{href}">{label}</a>'

    return f"""<nav class="top wrap-wide">
  <div>{item("index.html", "Quiet Sun", "index")} · MWA 2013–2015</div>
  <div>
    {item("images.html", "Images", "images")}
    &ensp;{item("runs.html", "Runs", "runs")}
  </div>
</nav>
"""


def foot() -> str:
    return """<footer class="wrap-wide">
  Brightness temperature in million K. Sharma &amp; Oberoi 2020.
  <a href="https://github.com/i4Ds/mwa-quiet-sun">Quiet Sun</a> ·
  <a href="https://github.com/i4Ds/mwa-flares">Flares</a>
</footer>
</body>
</html>
"""


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


MEDIA_FILES = {
    "fig4_vs_paircars.png": "quiet2015/fig4_vs_paircars.png",
    "fig4_162_vs_paircars.png": "quiet2015/fig4_162_vs_paircars.png",
    "fig4_his_mean.png": "sharma2020/fig4_his_mean.png",
    "fig4_ours_mean.png": "sharma2020/fig4_ours_mean.png",
    "fig4_his_vs_ours.png": "sharma2020/fig4_his_vs_ours.png",
    "fig4_diff.png": "sharma2020/fig4_diff.png",
    "fig4_paper.png": "sharma2020/fig4_paper.png",
    "fig4_ours_strip_108.png": "sharma2020/fig4_ours_strip_108.png",
    "fig4_ours_strip_162.png": "sharma2020/fig4_ours_strip_162.png",
    "fig4_ours_strip_217.png": "sharma2020/fig4_ours_strip_217.png",
    "fig4_ours_strip_240.png": "sharma2020/fig4_ours_strip_240.png",
    "haslam_sky.png": "sharma2020/haslam_sky.png",
    "compare_flux.png": "sharma2020/compare_flux.png",
    "fig4_raw_scanmean.png": "sharma2020/fig4_raw_scanmean.png",
    "fig4_snap_rohit_vs_casa.png": "sharma2020/fig4_snap_rohit_vs_casa.png",
    "uv_amp.png": "sharma2020/uv_amp.png",
    "snap_data_vs_corrected.png": "sharma2020/snap_data_vs_corrected.png",
}


def copy_media() -> dict[str, str]:
    MEDIA.mkdir(parents=True, exist_ok=True)
    out = {}
    for name, rel in MEDIA_FILES.items():
        src = FIG / rel
        if src.is_file():
            shutil.copy2(src, MEDIA / name)
            out[name] = f"media/{name}"
    return out


def figure(media: dict[str, str], name: str, alt: str, caption: str, *, prefix: str = "") -> str:
    src = media.get(name)
    if not src:
        return ""
    return (
        f'<div class="figure"><img src="{prefix}{src}" alt="{e(alt)}"></div>\n'
        f'<p class="caption">{caption}</p>\n'
    )


def facts(d: dict) -> str:
    if d["cal_obsid"] and d["dt_cal"] is not None:
        window = "within 24 h" if d["cal_within_24h"] else "outside 24 h"
        cal = (
            f'{e(d["cal_name"])} · {e(d["cal_obsid"])} · '
            f'{d["dt_cal"]:+.2f} h ({window})'
        )
    else:
        cal = "none listed"
    return f"""<dl class="facts">
  <div><dt>Observation</dt><dd>{e(d["obsid"])}</dd></div>
  <div><dt>Start</dt><dd>{e(fmt_time(d["start"]))}</dd></div>
  <div><dt>Length</dt><dd>{d["duration_s"]} s</dd></div>
  <div><dt>Elevation</dt><dd>{d["alt"]:.1f}°</dd></div>
  <div><dt>Hour angle</dt><dd>{d["ha"]:+.2f} h</dd></div>
  <div><dt>Calibrator</dt><dd>{cal}</dd></div>
</dl>
"""


def index_page(days: list[dict], media: dict[str, str]) -> str:
    n = len(days)
    n_cal = sum(1 for d in days if d["cal_within_24h"])
    n_map = sum(1 for d in days if d["status"] == "mapped")
    n_wait = sum(1 for d in days if d["status"] == "waiting")
    years = sorted({d["year"] for d in days})
    thumb = media.get("fig4_vs_paircars.png", "")

    chips = ['<button type="button" class="chip" data-year="all" aria-pressed="true">All years</button>']
    for y in years:
        chips.append(
            f'<button type="button" class="chip" data-year="{y}" aria-pressed="false">{y}</button>'
        )
    chips.append(
        '<button type="button" class="chip" data-filter="cal" aria-pressed="false">Calibrator within 24 h</button>'
    )
    chips.append(
        '<button type="button" class="chip" data-filter="work" aria-pressed="false">Imaged or in progress</button>'
    )

    blocks = []
    for y in years:
        ydays = [d for d in days if d["year"] == y]
        rows = []
        for d in ydays:
            alt_w = max(4, min(100, round(100 * d["alt"] / 90)))
            cal = d["cal_name"] if d["cal_name"] else "—"
            dt = f'{d["dt_cal"]:+.1f} h' if d["dt_cal"] is not None else "—"
            st = {
                "mapped": ("mapped", "Mapped"),
                "waiting": ("waiting", "In progress"),
                "none": ("none", "Not yet"),
            }[d["status"]]
            href = f'o/{d["obsid"]}.html'
            rows.append(
                f'<tr data-year="{d["year"]}" data-cal="{1 if d["cal_within_24h"] else 0}" '
                f'data-work="{1 if d["status"] != "none" else 0}" '
                f'data-text="{e((d["date"] + " " + d["obsid"] + " " + (d["cal_name"] or "")).lower())}">'
                f'<td><a class="date" href="{href}">{e(d["date"])}</a></td>'
                f'<td class="hide-sm mono">{e(d["obsid"])}</td>'
                f'<td><span class="altbar" title="{d["alt"]:.1f}°">'
                f'<i style="width:{alt_w}%"></i></span>{d["alt"]:.0f}°</td>'
                f'<td>{e(cal)}</td>'
                f'<td class="hide-sm">{e(dt)}</td>'
                f'<td class="status {st[0]}">{st[1]}</td>'
                f"</tr>"
            )
        blocks.append(
            f'<h2 class="year-head" data-year="{y}">{y}'
            f'<span class="year-n"> · {len(ydays)} days</span></h2>\n'
            f'<table class="days" data-year="{y}">'
            f"<thead><tr><th>Date</th><th class='hide-sm'>Sun obsid</th>"
            f"<th>Elevation</th><th>Calibrator</th>"
            f"<th class='hide-sm'>From cal</th><th>Maps</th></tr></thead>"
            f"<tbody>{''.join(rows)}</tbody></table>"
        )

    return (
        head("Quiet Sun, 2013–2015")
        + nav(current="index")
        + f"""<main class="wrap-wide">
  <p class="kicker">Murchison Widefield Array</p>
  <h1>Quiet Sun at local noon</h1>
  <p class="lede">
    GOES-quiet days, Sun within 30 minutes of local noon, 2013–2015.
  </p>
  <div class="stats">
    <div><b>{n}</b><span>quiet noon days</span></div>
    <div><b>{n_cal}</b><span>calibrator within 24 h</span></div>
    <div><b>{n_map}</b><span>with maps</span></div>
    <div><b>{n_wait}</b><span>imaging in progress</span></div>
  </div>

  <div class="featured">
    <a href="o/{FIG4_OBSID}.html">
      <p class="kicker">3 December 2015 · 03:39 UT</p>
      <h2>1133149192</h2>
      <p>Rohit, our remake, P-AIRCARS. 108 / 162 / 217 / 240 MHz. Solar north up.</p>
      <img src="{thumb}" alt="3 December 2015, four pipelines, four frequencies">
    </a>
    <a href="o/1133236216.html">
      <p class="kicker">4 December 2015 · 03:50 UT</p>
      <h2>1133236216</h2>
      <p>24.2 h later. CASA SuperUniform 0.5 s. Mean T_B running.</p>
      <div class="waiting">Mean running</div>
    </a>
    <a href="o/1111376776.html">
      <p class="kicker">26 March 2015 · 03:46 UT</p>
      <h2>1111376776</h2>
      <p>3C444, 2.45 h earlier. P-angle near 0°. ASVO 0.5 s / 4 s.</p>
      <div class="waiting">ASVO</div>
    </a>
  </div>

  <div class="toolbar">
    <input type="search" id="q" placeholder="Search date, obsid, calibrator" autocomplete="off">
    {"".join(chips)}
  </div>
  {"".join(blocks)}
</main>
"""
        + foot().replace("</body>", '<script src="js/catalogue.js"></script>\n</body>')
    )


def neighbours(days: list[dict], idx: int) -> tuple[dict | None, dict | None]:
    prev = days[idx - 1] if idx > 0 else None
    nxt = days[idx + 1] if idx + 1 < len(days) else None
    return prev, nxt


def pager_html(prev: dict | None, nxt: dict | None) -> str:
    left = (
        f'<a href="{prev["obsid"]}.html">← {e(fmt_date(prev["date"]))}</a>'
        if prev
        else "<span></span>"
    )
    right = (
        f'<a href="{nxt["obsid"]}.html">{e(fmt_date(nxt["date"]))} →</a>'
        if nxt
        else "<span></span>"
    )
    return f'<div class="pager">{left}{right}</div>'


def day_body(d: dict, media: dict[str, str]) -> str:
    if d["obsid"] == FIG4_NOON:
        return f"""
<p class="kicker">{e(fmt_date(d["date"]))} · local noon</p>
<h1>{e(d["obsid"])}</h1>
{facts(d)}
<p class="note">
  Figure 4 is <a href="{FIG4_OBSID}.html">{FIG4_OBSID}</a>, 03:39–03:44 UT,
  ten minutes earlier.
</p>
"""
    if d["obsid"] == "1133236216":
        return f"""
<p class="kicker">{e(fmt_date(d["date"]))} · 24.2 h after Figure 4</p>
<h1>{e(d["obsid"])}</h1>
{facts(d)}
<p>
  A co-rotating compact feature should shift 150–200 arcsec west.
  CASA SuperUniform 0.5 s frames are on the cluster. Mean T_B is running.
</p>
<p class="note"><a href="{FIG4_OBSID}.html">3 December 03:39 UT</a></p>
"""
    if d["obsid"] == "1111376776":
        return f"""
<p class="kicker">{e(fmt_date(d["date"]))}</p>
<h1>{e(d["obsid"])}</h1>
{facts(d)}
<p>
  CASA SuperUniform, 0.5 s Sun, 4 s 3C444. P-angle near 0°.
  ASVO jobs 1125020 (Sun) and 1125021 (3C444).
</p>
"""
    return f"""
<p class="kicker">{e(fmt_date(d["date"]))}</p>
<h1>{e(d["obsid"])}</h1>
{facts(d)}
"""


def day_page(d: dict, prev: dict | None, nxt: dict | None, media: dict[str, str]) -> str:
    return (
        head(f"{fmt_date(d['date'])} · Quiet Sun", root="..")
        + nav(root="..")
        + f'<main class="wrap">{day_body(d, media)}{pager_html(prev, nxt)}</main>'
        + foot()
    )


def fig4_page(media: dict[str, str], noon: dict | None) -> str:
    p = "../"
    back = f'{noon["obsid"]}.html' if noon else "../index.html"
    body = [
        f"""<p class="kicker">3 December 2015 · 03:39–03:44 UT</p>
<h1>{FIG4_OBSID}</h1>
<dl class="facts">
  <div><dt>Start</dt><dd>{e(fmt_time(FIG4_START))}</dd></div>
  <div><dt>Length</dt><dd>296 s</dd></div>
  <div><dt>Noon pick</dt><dd><a href="{FIG4_NOON}.html">{FIG4_NOON}</a></dd></div>
  <div><dt>P-angle</dt><dd>+15.4°</dd></div>
  <div><dt>CASA</dt><dd>SuperUniform, 570 × 0.5 s</dd></div>
  <div><dt>P-AIRCARS cal</dt><dd>3C444 · 1133161488</dd></div>
</dl>
""",
        figure(
            media, "fig4_vs_paircars.png",
            "Rohit, remake, P-AIRCARS self-cal, P-AIRCARS calibrator-only",
            "Solar north up. Peaks at 108 MHz: 0.89 / 0.89 / 0.82 / 0.83 million K. "
            "At 162 MHz: 0.99 / 1.01 / 0.88 / 0.90. At 217 and 240 MHz P-AIRCARS is noise.",
            prefix=p,
        ),
        figure(
            media, "fig4_his_mean.png",
            "Rohit mean of 570 frames",
            "Rohit, mean of 570 frames. Peaks 0.89 / 1.00 / 1.06 / 0.62 million K "
            "(paper captions 0.92 / 1.20 / 1.50 at 108 / 162 / 217 MHz).",
            prefix=p,
        ),
        figure(
            media, "fig4_ours_mean.png",
            "Our remake, mean of 570 frames",
            "Our remake, mean of 570 SuperUniform frames. Peaks 0.89 / 1.01 / 1.10 / 0.63 million K. "
            "Each panel scaled to its own peak.",
            prefix=p,
        ),
        figure(
            media, "fig4_his_vs_ours.png",
            "Rohit and our remake, same colour scale",
            "Rohit (top) and our remake (bottom), 0–1.7 million K, celestial north as in the FITS.",
            prefix=p,
        ),
        figure(
            media, "fig4_diff.png",
            "Ours minus Rohit",
            "Ours minus Rohit. Peak |Δ| 0.01 / 0.03 / 0.05 / 0.02 million K. Red: we are hotter.",
            prefix=p,
        ),
        figure(
            media, "fig4_paper.png",
            "MWA, FORWARD, AIA 193",
            "MWA (Rohit’s frames, Mohan then mean), FORWARD, AIA 193. MWA peaks 0.89 / 1.00 / 1.06 million K; "
            "FORWARD 1.66 / 1.69 / 1.70 million K.",
            prefix=p,
        ),
        figure(
            media, "fig4_ours_strip_108.png",
            "108 MHz half-second frames",
            "108 MHz, sample of the 570 half-second frames. Peak about 0.90 million K on each.",
            prefix=p,
        ),
        figure(
            media, "fig4_ours_strip_162.png",
            "162 MHz half-second frames",
            "162 MHz, sample of the 570 half-second frames.",
            prefix=p,
        ),
        figure(
            media, "fig4_ours_strip_217.png",
            "217 MHz half-second frames",
            "217 MHz, sample of the 570 half-second frames.",
            prefix=p,
        ),
        figure(
            media, "fig4_ours_strip_240.png",
            "240 MHz half-second frames",
            "240 MHz, sample of the 570 half-second frames.",
            prefix=p,
        ),
        figure(
            media, "haslam_sky.png",
            "Haslam 1982 sky at the 3 December 2015 pointing",
            "Haslam et al. 1982 at this pointing, 3 December 2015 03:42 UT. Galactic plane is close; "
            "Sun marked on the right.",
            prefix=p,
        ),
        figure(
            media, "compare_flux.png",
            "Whole-Sun flux at four frequencies",
            "Whole-Sun flux at this pointing: 2.9 / 6.5 / 11.7 / 8.2 solar flux units "
            "at 108 / 162 / 217 / 240 MHz (Haslam 1982 sky). Grey: Oberoi 2013 table, a different day.",
            prefix=p,
        ),
        figure(
            media, "fig4_162_vs_paircars.png",
            "162 MHz versus P-AIRCARS at 145.9 MHz",
            "162 MHz (Rohit, remake) against P-AIRCARS at 145.9 MHz (pair 113–114). Solar north up.",
            prefix=p,
        ),
        figure(
            media, "fig4_raw_scanmean.png",
            "P-AIRCARS visibilities, 280 s CASA mean",
            "P-AIRCARS-calibrated visibilities, CASA SuperUniform, 280 s mean, Jy/beam. Not the 570-frame T_B mean.",
            prefix=p,
        ),
        figure(
            media, "fig4_snap_rohit_vs_casa.png",
            "One 0.5 s snapshot, Rohit versus applycal of Cen A",
            "One 0.5 s snapshot, 03:42:04 UT, 108 MHz, same Jy/beam scale. "
            "Rohit CORRECTED_DATA 36 Jy/beam; CASA applycal of his Cen A table 12 Jy/beam.",
            prefix=p,
        ),
        f'<div class="pager"><a href="{back}">Noon pick {FIG4_NOON}</a>'
        f'<a href="../images.html">All images</a></div>',
    ]
    return (
        head("3 December 2015 · 1133149192", root="..")
        + nav(root="..")
        + f'<main class="wrap">{"".join(body)}</main>'
        + foot()
    )


def images_page(media: dict[str, str]) -> str:
    blocks = [
        """<p class="kicker">3 December 2015 · 03:39 UT · 1133149192</p>
<h1>Images</h1>
""",
        figure(
            media, "fig4_vs_paircars.png",
            "Four pipelines, four frequencies",
            "Rohit, remake, P-AIRCARS self-cal, P-AIRCARS calibrator-only. Solar north up. "
            "Peaks at 108 MHz: 0.89 / 0.89 / 0.82 / 0.83 million K. At 217 and 240 MHz P-AIRCARS is noise.",
        ),
        figure(
            media, "fig4_his_mean.png",
            "Rohit mean of 570 frames",
            "Rohit, mean of 570 frames. 0.89 / 1.00 / 1.06 / 0.62 million K.",
        ),
        figure(
            media, "fig4_ours_mean.png",
            "Remake mean of 570 frames",
            "Remake, mean of 570 SuperUniform frames. 0.89 / 1.01 / 1.10 / 0.63 million K.",
        ),
        figure(
            media, "fig4_his_vs_ours.png",
            "Rohit and remake, same scale",
            "Rohit (top) and remake (bottom), 0–1.7 million K.",
        ),
        figure(
            media, "fig4_diff.png",
            "Remake minus Rohit",
            "Remake minus Rohit. Peak |Δ| 0.01 / 0.03 / 0.05 / 0.02 million K.",
        ),
        figure(
            media, "fig4_paper.png",
            "MWA, FORWARD, AIA 193",
            "MWA, FORWARD, AIA 193. MWA 0.89 / 1.00 / 1.06 million K; FORWARD 1.66 / 1.69 / 1.70 million K.",
        ),
        figure(
            media, "fig4_ours_strip_108.png",
            "108 MHz half-second frames",
            "108 MHz, sample of 570 × 0.5 s.",
        ),
        figure(
            media, "fig4_ours_strip_162.png",
            "162 MHz half-second frames",
            "162 MHz, sample of 570 × 0.5 s.",
        ),
        figure(
            media, "fig4_ours_strip_217.png",
            "217 MHz half-second frames",
            "217 MHz, sample of 570 × 0.5 s.",
        ),
        figure(
            media, "fig4_ours_strip_240.png",
            "240 MHz half-second frames",
            "240 MHz, sample of 570 × 0.5 s.",
        ),
        figure(
            media, "haslam_sky.png",
            "Haslam 1982 at this pointing",
            "Haslam et al. 1982, 3 December 2015 03:42 UT.",
        ),
        figure(
            media, "compare_flux.png",
            "Whole-Sun flux",
            "2.9 / 6.5 / 11.7 / 8.2 solar flux units at 108 / 162 / 217 / 240 MHz.",
        ),
        figure(
            media, "fig4_162_vs_paircars.png",
            "162 MHz versus P-AIRCARS 145.9 MHz",
            "162 MHz against P-AIRCARS pair 113–114 (145.9 MHz).",
        ),
        figure(
            media, "fig4_raw_scanmean.png",
            "280 s mean, Jy/beam",
            "P-AIRCARS visibilities, CASA SuperUniform, 280 s mean, Jy/beam.",
        ),
        figure(
            media, "fig4_snap_rohit_vs_casa.png",
            "One 0.5 s snapshot, 108 MHz",
            "03:42:04 UT. Rohit 36 Jy/beam; applycal of his Cen A table 12 Jy/beam.",
        ),
        figure(
            media, "uv_amp.png",
            "Visibility amplitude versus baseline",
            "Channel 84, 0.5 s, 8000 rows near mid-scan. DATA and CORRECTED_DATA.",
        ),
        figure(
            media, "snap_data_vs_corrected.png",
            "DATA versus CORRECTED_DATA snapshot",
            "One snapshot, DATA against CORRECTED_DATA.",
        ),
        f'<p class="note"><a href="o/{FIG4_OBSID}.html">{FIG4_OBSID}</a></p>',
    ]
    return (
        head("Images · Quiet Sun")
        + nav(current="images")
        + f'<main class="wrap">{"".join(blocks)}</main>'
        + foot()
    )


def runs_page() -> str:
    return (
        head("Runs · Quiet Sun")
        + nav(current="runs")
        + """<main class="wrap-wide">
<p class="kicker">MWA</p>
<h1>Runs</h1>
<table class="days">
<thead><tr><th>Day</th><th>Observation</th><th>What</th><th>Result</th></tr></thead>
<tbody>
<tr>
  <td>3 Dec 2015 03:39</td>
  <td class="mono">1133149192</td>
  <td>CASA SuperUniform, Hogbom niter 8000, 570 × 0.5 s, Mohan 5σ, scan mean</td>
  <td>0.89 / 1.01 / 1.10 / 0.63 million K</td>
</tr>
<tr>
  <td>3 Dec 2015 03:39</td>
  <td class="mono">1133149192</td>
  <td>P-AIRCARS, 4 s, 3C444 1133161488, pairs 84–85, 125–126, 169–170, 187–188</td>
  <td>Disk at 108 and 162 MHz. Noise at 217 and 240 MHz.</td>
</tr>
<tr>
  <td>3 Dec 2015 03:39</td>
  <td class="mono">1133149192</td>
  <td>P-AIRCARS pair 113–114, 145.9 MHz, same 4 s recipe</td>
  <td>Disk. Peak 1.04 million K (self-cal), 0.82 (calibrator only).</td>
</tr>
<tr>
  <td>3 Dec 2015 03:42</td>
  <td class="mono">1133149192</td>
  <td>Haslam 1982 sky at this pointing, 4×4 array factor</td>
  <td>2.9 / 6.5 / 11.7 / 8.2 solar flux units</td>
</tr>
<tr>
  <td>4 Dec 2015 03:50</td>
  <td class="mono">1133236216</td>
  <td>CASA SuperUniform 0.5 s, Cen A 1133236576, same channels as Figure 4</td>
  <td>Frames on cluster. Mean T_B running (qn-mean 230745).</td>
</tr>
<tr>
  <td>26 Mar 2015 03:46</td>
  <td class="mono">1111376776</td>
  <td>ASVO Sun 0.5 s 160 kHz no_rfi (1125020), 3C444 4 s (1125021)</td>
  <td>Download watching (qm-asvo-watch 230744).</td>
</tr>
</tbody>
</table>
<p class="note">
  Weighting SuperUniform, not Briggs. Conversion Mohan &amp; Oberoi 2017, not a 2022 scale factor.
  P-AIRCARS is a separate column, not inside the CASA remake.
</p>
</main>
"""
        + foot()
    )


def catalogue_js() -> str:
    return """(function () {
  const q = document.getElementById("q");
  const chips = [...document.querySelectorAll(".chip")];
  let year = "all";
  let calOnly = false;
  let workOnly = false;

  function apply() {
    const needle = (q.value || "").trim().toLowerCase();
    document.querySelectorAll("table.days tbody tr").forEach((tr) => {
      const y = tr.getAttribute("data-year");
      const cal = tr.getAttribute("data-cal") === "1";
      const work = tr.getAttribute("data-work") === "1";
      const text = tr.getAttribute("data-text") || "";
      let ok = year === "all" || y === year;
      if (calOnly && !cal) ok = false;
      if (workOnly && !work) ok = false;
      if (needle && !text.includes(needle)) ok = false;
      tr.classList.toggle("hidden", !ok);
    });
    document.querySelectorAll(".year-head, table.days").forEach((el) => {
      const y = el.getAttribute("data-year");
      const table = document.querySelector("table.days[data-year='" + y + "']");
      const any = table && [...table.querySelectorAll("tbody tr")].some((tr) => !tr.classList.contains("hidden"));
      const showYear = (year === "all" || y === year) && any;
      el.classList.toggle("hidden", !showYear);
    });
  }

  chips.forEach((btn) => {
    btn.addEventListener("click", () => {
      if (btn.dataset.year) {
        year = btn.dataset.year;
        chips.filter((c) => c.dataset.year).forEach((c) =>
          c.setAttribute("aria-pressed", c === btn ? "true" : "false"));
      } else if (btn.dataset.filter === "cal") {
        calOnly = !calOnly;
        btn.setAttribute("aria-pressed", calOnly ? "true" : "false");
      } else if (btn.dataset.filter === "work") {
        workOnly = !workOnly;
        btn.setAttribute("aria-pressed", workOnly ? "true" : "false");
      }
      apply();
    });
  });
  q.addEventListener("input", apply);
})();
"""


def main() -> None:
    days = load_days()
    SITE.mkdir(parents=True, exist_ok=True)
    media = copy_media()
    write(SITE / ".nojekyll", "")
    about = SITE / "about.html"
    if about.exists():
        about.unlink()
    write(SITE / "js/catalogue.js", catalogue_js())
    write(SITE / "index.html", index_page(days, media))
    write(SITE / "images.html", images_page(media))
    write(SITE / "runs.html", runs_page())
    write(
        SITE / "compare.html",
        '<!DOCTYPE html><meta http-equiv="refresh" content="0; url=images.html">',
    )
    noon = next((d for d in days if d["obsid"] == FIG4_NOON), None)
    write(SITE / "o" / f"{FIG4_OBSID}.html", fig4_page(media, noon))
    for i, d in enumerate(days):
        prev, nxt = neighbours(days, i)
        write(SITE / "o" / f'{d["obsid"]}.html', day_page(d, prev, nxt, media))
    print(f"wrote {len(days) + 1} observation pages under {SITE}")


if __name__ == "__main__":
    main()
