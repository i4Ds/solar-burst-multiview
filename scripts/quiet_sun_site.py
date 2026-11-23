#!/usr/bin/env python3
"""Build the quiet-Sun comparison site from the 2013–2015 noon catalogue.

Writes static HTML under site/quiet-sun/. Published as the private
i4Ds/mwa-quiet-sun repo. A day is mapped only when a figure already
exists on disk. Does not invent maps.
"""

from __future__ import annotations

import csv
import html
import json
import shutil
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "configs/quiet/quiet_noon_2013_2015.csv"
SITE = ROOT / "site/quiet-sun"
MEDIA = SITE / "media"
FIG = ROOT / "figures"
POINTING_DIR = FIG / "quiet2015" / "pointing"
POINTING_JSON = POINTING_DIR / "pointing.json"

# Sharma & Oberoi 2020 Fig. 4: not the noon pick that day.
FIG4_OBSID = "1133149192"
FIG4_NOON = "1133149792"
FIG4_START = "2015-12-03T03:39:44"
FIG4_DURATION_S = 296
FIG4_DATE = "2015-12-03"

# Noon-list status. Figure 4 is 1133149192 (03:39 UT). The catalogue row
# 1133149792 is the 03:49 noon pick; maps there are Rohit's FITS, not a
# CASA remake. 4 December 1133236216 has a CASA mean map.
WORK = {
    "1133149792": "mapped",
    "1133236216": "mapped",
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
                    "interval": fmt_interval(start, int(float(r["duration"]))),
                    "heading": fmt_heading(
                        date, start, int(float(r["duration"]))
                    ),
                }
            )
    return rows


def e(s: object) -> str:
    return html.escape(str(s), quote=True)


def fmt_date(iso: str) -> str:
    return datetime.strptime(iso, "%Y-%m-%d").strftime("%-d %B %Y")


def fmt_date_short(iso: str) -> str:
    return datetime.strptime(iso, "%Y-%m-%d").strftime("%-d %b %Y")


def parse_start(iso: str) -> datetime:
    return datetime.strptime(iso, "%Y-%m-%dT%H:%M:%S")


def fmt_interval(start_iso: str, duration_s: int) -> str:
    t0 = parse_start(start_iso)
    t1 = t0 + timedelta(seconds=int(duration_s))
    return f"{t0:%H:%M}–{t1:%H:%M} UT"


def fmt_heading(date_iso: str, start_iso: str, duration_s: int) -> str:
    return f"{fmt_date(date_iso)}, {fmt_interval(start_iso, duration_s)}"


FIG4_INTERVAL = fmt_interval(FIG4_START, FIG4_DURATION_S)
FIG4_HEADING = fmt_heading(FIG4_DATE, FIG4_START, FIG4_DURATION_S)
FIG4_EVENT = {
    "obsid": FIG4_OBSID,
    "date": FIG4_DATE,
    "start": FIG4_START,
    "duration_s": FIG4_DURATION_S,
    "interval": FIG4_INTERVAL,
    "heading": FIG4_HEADING,
    "alt": None,
    "ha": None,
    "cal_obsid": "1133139776",
    "cal_name": "CenA",
    "dt_cal": None,
    "cal_within_24h": True,
}

# Extra facts after the common block, same labels and order when present.
EXTRAS = {
    FIG4_OBSID: [
        ("P-angle", "+15.4°"),
        ("Images", "CASA SuperUniform, 570 × 0.5 s"),
        ("Flux", "Haslam 1982 at this pointing"),
    ],
    FIG4_NOON: [
        ("P-angle", "+15.4°"),
        ("Images", "Rohit's SuperUniform FITS, 570 × 0.5 s"),
        ("Flux", "Haslam 1982 at this pointing"),
    ],
    "1133236216": [
        ("P-angle", "+15.0°"),
        ("Images", "CASA SuperUniform, 579 × 0.5 s"),
        ("Flux", "Oberoi 2017 Table 1 (2013 pointing)"),
    ],
}


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
    "dec4_ours_mean.png": "quiet2015/dec4_ours_mean.png",
    "fig4_vs_dec4.png": "quiet2015/fig4_vs_dec4.png",
    "dec3_noon_rohit_mean.png": "quiet2015/dec3_noon_rohit_mean.png",
}


def load_pointing() -> dict[str, dict]:
    if not POINTING_JSON.is_file():
        return {}
    return json.loads(POINTING_JSON.read_text())


def apply_pointing(d: dict, recs: dict[str, dict]) -> None:
    rec = recs.get(d["obsid"])
    if not rec:
        return
    d["az"] = rec.get("az_deg")
    d["za"] = rec.get("za_deg")
    d["pointing_mid"] = rec.get("mid")
    if d.get("alt") is None and rec.get("alt_deg") is not None:
        d["alt"] = rec["alt_deg"]


def copy_media() -> dict[str, str]:
    MEDIA.mkdir(parents=True, exist_ok=True)
    out = {}
    for name, rel in MEDIA_FILES.items():
        src = FIG / rel
        if src.is_file():
            shutil.copy2(src, MEDIA / name)
            out[name] = f"media/{name}"
    dest = MEDIA / "pointing"
    dest.mkdir(parents=True, exist_ok=True)
    if POINTING_DIR.is_dir():
        for png in sorted(POINTING_DIR.glob("*.png")):
            shutil.copy2(png, dest / png.name)
            key = f"pointing/{png.name}"
            out[key] = f"media/{key}"
    return out


def figure(media: dict[str, str], name: str, alt: str, caption: str, *, prefix: str = "") -> str:
    src = media.get(name)
    if not src:
        return ""
    return (
        f'<div class="figure"><img src="{prefix}{src}" alt="{e(alt)}"></div>\n'
        f'<p class="caption">{caption}</p>\n'
    )


def pointing_figure(media: dict[str, str], d: dict, *, prefix: str = "") -> str:
    mid = d.get("pointing_mid")
    if mid:
        t = datetime.strptime(mid, "%Y-%m-%dT%H:%M:%S")
        when = f"{t:%-d %B %Y} {t:%H:%M} UT"
    else:
        when = d.get("heading") or "this pointing"
    return figure(
        media,
        f"pointing/{d['obsid']}.png",
        "Haslam 1982 at this pointing",
        (
            f"Haslam et al. 1982 at this pointing, {when}. "
            "Tile beam 90 / 9 / 0.9 % on the right. Sun in yellow."
        ),
        prefix=prefix,
    )


def calibrator_text(d: dict) -> str:
    if d.get("cal_obsid") and d.get("dt_cal") is not None:
        window = "within 24 h" if d.get("cal_within_24h") else "outside 24 h"
        return (
            f'{e(d["cal_name"])} · {e(d["cal_obsid"])} · '
            f'{d["dt_cal"]:+.2f} h ({window})'
        )
    if d.get("cal_obsid"):
        name = e(d["cal_name"]) + " · " if d.get("cal_name") else ""
        return f'{name}{e(d["cal_obsid"])}'
    return "none listed"


def facts(d: dict, extra: list[tuple[str, str]] | None = None) -> str:
    items: list[tuple[str, str]] = [
        ("Time", d["interval"]),
        ("Observation", d["obsid"]),
        (
            "Elevation",
            f'{d["alt"]:.1f}°' if d.get("alt") is not None else "—",
        ),
        (
            "Hour angle",
            f'{d["ha"]:+.2f} h' if d.get("ha") is not None else "—",
        ),
        (
            "Azimuth",
            f'{d["az"]:.1f}°' if d.get("az") is not None else "—",
        ),
        (
            "Zenith",
            f'{d["za"]:.1f}°' if d.get("za") is not None else "—",
        ),
        ("Calibrator", calibrator_text(d)),
    ]
    if extra:
        items.extend(extra)
    rows = "".join(
        f"<div><dt>{e(k)}</dt><dd>{v if k == 'Calibrator' else e(v)}</dd></div>"
        for k, v in items
    )
    return f'<dl class="facts">{rows}</dl>\n'


def index_page(days: list[dict], media: dict[str, str]) -> str:
    n = len(days)
    n_cal = sum(1 for d in days if d["cal_within_24h"])
    n_map = sum(1 for d in days if d["status"] == "mapped")
    n_wait = sum(1 for d in days if d["status"] == "waiting")
    years = sorted({d["year"] for d in days})
    thumb = media.get("fig4_vs_paircars.png", "")
    thumb_noon = media.get("dec3_noon_rohit_mean.png", "")
    thumb4 = media.get("dec4_ours_mean.png", "")
    noon = next((d for d in days if d["obsid"] == FIG4_NOON), None)
    dec4 = next((d for d in days if d["obsid"] == "1133236216"), None)
    noon_interval = noon["interval"] if noon else fmt_interval("2015-12-03T03:49:35", 296)
    dec4_interval = dec4["interval"] if dec4 else fmt_interval("2015-12-04T03:49:59", 296)
    noon_heading = noon["heading"] if noon else fmt_heading(FIG4_DATE, "2015-12-03T03:49:35", 296)
    dec4_heading = dec4["heading"] if dec4 else fmt_heading("2015-12-04", "2015-12-04T03:49:59", 296)

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
            search = (
                d["date"] + " " + d["heading"] + " " + d["obsid"] + " "
                + (d["cal_name"] or "")
            )
            if d["obsid"] == FIG4_NOON:
                search += " " + FIG4_OBSID + " " + FIG4_HEADING
            rows.append(
                f'<tr data-year="{d["year"]}" data-cal="{1 if d["cal_within_24h"] else 0}" '
                f'data-work="{1 if d["status"] != "none" else 0}" '
                f'data-text="{e(search.lower())}">'
                f'<td><a class="date" href="{href}">{e(fmt_date_short(d["date"]))}</a></td>'
                f'<td>{e(d["interval"])}</td>'
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
            f"<thead><tr><th>Date</th><th>Time</th>"
            f"<th class='hide-sm'>Observation</th>"
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
      <p class="kicker">{e(fmt_date(FIG4_DATE))}</p>
      <h2>{e(FIG4_INTERVAL)}</h2>
      <p>108 / 162 / 217 / 240 MHz. Solar north up.</p>
      <img src="{thumb}" alt="{e(FIG4_HEADING)}, four pipelines, four frequencies">
    </a>
    <a href="o/{FIG4_NOON}.html#noon">
      <p class="kicker">{e(fmt_date(FIG4_DATE))}</p>
      <h2>{e(noon_interval)}</h2>
      <p>108 / 162 / 217 / 240 MHz. Solar north up.</p>
      <img src="{thumb_noon}" alt="{e(noon_heading)}, four frequencies">
    </a>
    <a href="o/1133236216.html">
      <p class="kicker">4 December 2015</p>
      <h2>{e(dec4_interval)}</h2>
      <p>108 / 162 / 217 / 240 MHz. Solar north up.</p>
      <img src="{thumb4}" alt="{e(dec4_heading)}, four frequencies">
    </a>
  </div>

  <div class="toolbar">
    <input type="search" id="q" placeholder="Search date, time, calibrator" autocomplete="off">
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
        f'<a href="{prev["obsid"]}.html">← {e(prev["heading"])}</a>'
        if prev
        else "<span></span>"
    )
    right = (
        f'<a href="{nxt["obsid"]}.html">{e(nxt["heading"])} →</a>'
        if nxt
        else "<span></span>"
    )
    return f'<div class="pager">{left}{right}</div>'


def day_intro() -> str:
    return '<p class="kicker">Quiet Sun</p>\n'


def day_body(d: dict, media: dict[str, str]) -> str:
    if d["obsid"] == FIG4_NOON:
        return (
            f"""
{day_intro()}<h1>{e(fmt_date(d["date"]))}</h1>
<p class="lede">Two Sun scans. Maps on both.</p>
<h2 class="section">{e(FIG4_INTERVAL)}</h2>
{facts(FIG4_EVENT, EXTRAS[FIG4_OBSID])}
"""
            + figure(
                media, "fig4_vs_paircars.png",
                "Rohit, remake, P-AIRCARS self-cal, P-AIRCARS calibrator-only",
                "Solar north up. Peaks at 108 MHz: 0.89 / 0.89 / 0.82 / 0.83 million K. "
                "At 162 MHz: 0.99 / 1.01 / 0.88 / 0.90. At 217 and 240 MHz P-AIRCARS is noise.",
                prefix="../",
            )
            + figure(
                media, "fig4_ours_mean.png",
                "Our remake, mean of 570 frames",
                "Our remake, mean of 570 SuperUniform frames. Peaks 0.89 / 1.01 / 1.10 / 0.63 million K. "
                "Each panel scaled to its own peak.",
                prefix="../",
            )
            + pointing_figure(media, FIG4_EVENT, prefix="../")
            + f'<p class="note"><a href="{FIG4_OBSID}.html">{e(FIG4_HEADING)}</a></p>\n'
            + f"""
<h2 class="section" id="noon">{e(d["interval"])}</h2>
{facts(d, EXTRAS[FIG4_NOON])}
"""
            + figure(
                media, "dec3_noon_rohit_mean.png",
                f"{d['heading']}, 108 / 162 / 217 / 240 MHz",
                "Rohit's images, mean of 570 × 0.5 s after Mohan 5σ. "
                "Haslam 1982 at this pointing, not Oberoi 2017 Table 1. "
                "Solar north up. Each panel scaled to its own peak. "
                "Peaks 1.15 / 1.43 / 1.39 / 0.78 MK. "
                "Whole-Sun flux 3.52 / 8.15 / 14.61 / 9.67 solar flux units. "
                "Mohan F(ν) = 41 / 302 / 49 / 103. The 162 MHz conversion is large; "
                "the mean is still a disk.",
                prefix="../",
            )
            + pointing_figure(media, d, prefix="../")
        )
    extras = EXTRAS.get(d["obsid"])
    head_block = f"""
{day_intro()}<h1>{e(d["heading"])}</h1>
{facts(d, extras)}
"""
    if d["obsid"] == "1133236216":
        return head_block + figure(
            media, "dec4_ours_mean.png",
            f"{d['heading']}, 108 / 162 / 217 / 240 MHz",
            "CASA SuperUniform, mean of 579 × 0.5 s. Solar north up. "
            "Peaks 0.29 / 0.33 / 0.51 / 0.70 million K. "
            "Whole-Sun flux 0.86 / 2.22 / 5.99 / 5.35 solar flux units from "
            "Oberoi 2017 Table 1 (a 2013 pointing), not Haslam at this pointing. "
            "240 MHz Mohan F(ν) = 532; that panel is not a disk.",
            prefix="../",
        ) + figure(
            media, "fig4_vs_dec4.png",
            "3 December remake above, 4 December below",
            "Each panel scaled to its own peak. Solar north up. "
            f"Top: {FIG4_HEADING}. Bottom: {d['heading']}.",
            prefix="../",
        ) + pointing_figure(media, d, prefix="../") + (
            f'<p class="note"><a href="{FIG4_OBSID}.html">{e(FIG4_HEADING)}</a></p>'
        )
    return head_block + pointing_figure(media, d, prefix="../")


def day_page(d: dict, prev: dict | None, nxt: dict | None, media: dict[str, str]) -> str:
    title = fmt_date(d["date"]) if d["obsid"] == FIG4_NOON else d["heading"]
    return (
        head(f"{title} · Quiet Sun", root="..")
        + nav(root="..")
        + f'<main class="wrap">{day_body(d, media)}{pager_html(prev, nxt)}</main>'
        + foot()
    )


def fig4_page(media: dict[str, str], noon: dict | None) -> str:
    p = "../"
    back = f'{noon["obsid"]}.html' if noon else "../index.html"
    body = [
        f"""<p class="kicker">Quiet Sun</p>
<h1>{e(FIG4_HEADING)}</h1>
{facts(FIG4_EVENT, EXTRAS[FIG4_OBSID])}
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
        pointing_figure(media, FIG4_EVENT, prefix=p),
        f'<div class="pager"><a href="{back}">{e(noon["heading"]) if noon else "Catalogue"}</a>'
        f'<a href="../images.html">All images</a></div>',
    ]
    return (
        head(f"{FIG4_HEADING} · Quiet Sun", root="..")
        + nav(root="..")
        + f'<main class="wrap">{"".join(body)}</main>'
        + foot()
    )


def images_page(media: dict[str, str], days: list[dict]) -> str:
    noon = next((d for d in days if d["obsid"] == FIG4_NOON), None)
    dec4 = next((d for d in days if d["obsid"] == "1133236216"), None)
    blocks = [
        f"""<p class="kicker">Quiet Sun</p>
<h1>Images</h1>
<h2 class="section">{e(FIG4_HEADING)}</h2>
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
        pointing_figure(media, FIG4_EVENT),
        f'<p class="note"><a href="o/{FIG4_OBSID}.html">{e(FIG4_HEADING)}</a></p>',
        f"""<h2 class="section">{e(fmt_heading(FIG4_DATE, "2015-12-03T03:49:35", 296))}</h2>
""",
        figure(
            media, "dec3_noon_rohit_mean.png",
            "3 December 2015 03:49 UT, four frequencies",
            "Rohit's SuperUniform images, mean of 570 × 0.5 s after Mohan 5σ. "
            "Haslam 1982 at this pointing. Solar north up. "
            "Peaks 1.15 / 1.43 / 1.39 / 0.78 MK. "
            "Flux 3.52 / 8.15 / 14.61 / 9.67 solar flux units. "
            "F(ν) = 41 / 302 / 49 / 103. The 162 MHz conversion is large; "
            "the mean is still a disk.",
        ),
        pointing_figure(media, noon) if noon else "",
        f'<p class="note"><a href="o/{FIG4_NOON}.html#noon">{e(fmt_heading(FIG4_DATE, "2015-12-03T03:49:35", 296))}</a></p>',
        f"""<h2 class="section">{e(fmt_heading("2015-12-04", "2015-12-04T03:49:59", 296))}</h2>
""",
        figure(
            media, "dec4_ours_mean.png",
            "4 December 2015, four frequencies",
            "CASA SuperUniform, mean of 579 × 0.5 s. Solar north up. "
            "Peaks 0.29 / 0.33 / 0.51 / 0.70 million K. "
            "Flux 0.86 / 2.22 / 5.99 / 5.35 solar flux units (Oberoi 2017 Table 1, 2013 pointing). "
            "240 MHz Mohan F(ν) = 532; that panel is not a disk.",
        ),
        figure(
            media, "fig4_vs_dec4.png",
            "3 December remake above, 4 December below",
            "Each panel scaled to its own peak. Solar north up. "
            "Top: Figure 4 remake. Bottom: 4 December noon scan.",
        ),
        pointing_figure(media, dec4) if dec4 else "",
        f'<p class="note"><a href="o/1133236216.html">{e(fmt_heading("2015-12-04", "2015-12-04T03:49:59", 296))}</a></p>',
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
<thead><tr><th>Time</th><th>Observation</th><th>What</th><th>Result</th></tr></thead>
<tbody>
<tr>
  <td>3 December 2015, 03:39–03:44 UT</td>
  <td class="mono">1133149192</td>
  <td>CASA SuperUniform, Hogbom niter 8000, 570 × 0.5 s, Mohan 5σ, scan mean</td>
  <td>0.89 / 1.01 / 1.10 / 0.63 million K</td>
</tr>
<tr>
  <td>3 December 2015, 03:39–03:44 UT</td>
  <td class="mono">1133149192</td>
  <td>P-AIRCARS, 4 s, 3C444 1133161488, pairs 84–85, 125–126, 169–170, 187–188</td>
  <td>Disk at 108 and 162 MHz. Noise at 217 and 240 MHz.</td>
</tr>
<tr>
  <td>3 December 2015, 03:39–03:44 UT</td>
  <td class="mono">1133149192</td>
  <td>P-AIRCARS pair 113–114, 145.9 MHz, same 4 s recipe</td>
  <td>Disk. Peak 1.04 million K (self-cal), 0.82 (calibrator only).</td>
</tr>
<tr>
  <td>3 December 2015, 03:39–03:44 UT</td>
  <td class="mono">1133149192</td>
  <td>Haslam 1982 sky at this pointing, 4×4 array factor</td>
  <td>2.9 / 6.5 / 11.7 / 8.2 solar flux units</td>
</tr>
<tr>
  <td>3 December 2015, 03:49–03:54 UT</td>
  <td class="mono">1133149792</td>
  <td>Rohit's SuperUniform FITS, 570 × 0.5 s, Mohan 5σ, Haslam 1982 at this pointing</td>
  <td>1.15 / 1.43 / 1.39 / 0.78 MK. F(ν) = 41 / 302 / 49 / 103.</td>
</tr>
<tr>
  <td>4 December 2015, 03:49–03:54 UT</td>
  <td class="mono">1133236216</td>
  <td>CASA SuperUniform, Hogbom niter 8000, 579 × 0.5 s, Mohan 5σ, Oberoi 2017 Table 1 flux</td>
  <td>0.29 / 0.33 / 0.51 / 0.70 million K. 240 MHz F(ν) = 532.</td>
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
    recs = load_pointing()
    apply_pointing(FIG4_EVENT, recs)
    for d in days:
        apply_pointing(d, recs)
    SITE.mkdir(parents=True, exist_ok=True)
    media = copy_media()
    write(SITE / ".nojekyll", "")
    about = SITE / "about.html"
    if about.exists():
        about.unlink()
    write(SITE / "js/catalogue.js", catalogue_js())
    write(SITE / "index.html", index_page(days, media))
    write(SITE / "images.html", images_page(media, days))
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
