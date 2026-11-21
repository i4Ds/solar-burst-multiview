#!/usr/bin/env python3
"""Build the quiet-Sun comparison site from the 2013–2015 noon catalogue.

Writes static HTML under site/quiet-sun/. A day is mapped only when a
figure already exists on disk. Does not invent maps.
"""

from __future__ import annotations

import csv
import html
import shutil
from datetime import datetime, timezone
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
WORK = {
    FIG4_NOON: "mapped",  # maps are the 03:39 scan, not this noon pick
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
    {item("compare.html", "Comparisons", "compare")}
    &ensp;{item("about.html", "About", "about")}
  </div>
</nav>
"""


def foot() -> str:
    return """<footer class="wrap-wide">
  Sharma &amp; Oberoi 2020 quiet-Sun catalogue. Brightness temperature in million K.
  Maps are shown only when they exist; empty days are waiting, not missing science.
</footer>
</body>
</html>
"""


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def copy_media() -> dict[str, str]:
    MEDIA.mkdir(parents=True, exist_ok=True)
    files = {
        "fig4_vs_paircars.png": FIG / "quiet2015/fig4_vs_paircars.png",
        "fig4_his_vs_ours.png": FIG / "sharma2020/fig4_his_vs_ours.png",
        "fig4_his_mean.png": FIG / "sharma2020/fig4_his_mean.png",
        "fig4_ours_mean.png": FIG / "sharma2020/fig4_ours_mean.png",
    }
    out = {}
    for name, src in files.items():
        if src.is_file():
            dest = MEDIA / name
            shutil.copy2(src, dest)
            out[name] = f"media/{name}"
    return out


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
            if d["obsid"] == FIG4_NOON:
                st = ("mapped", "See Figure 4")
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
    Every MWA solar pointing within 30 minutes of local noon on a GOES-quiet
    day, 2013–2015. The catalogue is the starting point. Maps appear only
    after a day is imaged; most pages are empty on purpose.
  </p>
  <div class="stats">
    <div><b>{n}</b><span>quiet noon days</span></div>
    <div><b>{n_cal}</b><span>calibrator within 24 h</span></div>
    <div><b>{n_map}</b><span>with maps on this site</span></div>
    <div><b>{n_wait}</b><span>imaging in progress</span></div>
  </div>

  <p class="kicker">Now on the table</p>
  <div class="featured">
    <a href="o/{FIG4_OBSID}.html">
      <p class="kicker">3 December 2015 · 03:39 UT</p>
      <h2>Figure 4, four ways</h2>
      <p>Rohit, our remake, P-AIRCARS with self-cal, P-AIRCARS from the calibrator only. Solar north up.</p>
      <img src="{thumb}" alt="">
    </a>
    <a href="o/1133236216.html">
      <p class="kicker">4 December 2015</p>
      <h2>One day later</h2>
      <p>Same local time. A co-rotating blob should move west by about one beam. Mean maps are running.</p>
      <div class="waiting">In progress</div>
    </a>
    <a href="o/1111376776.html">
      <p class="kicker">26 March 2015</p>
      <h2>A different season</h2>
      <p>Same CASA recipe, P-angle near zero. Archive download submitted; this page stays empty until the maps exist.</p>
      <div class="waiting">Queued</div>
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
<p class="kicker">{e(fmt_date(d["date"]))} · local-noon pick</p>
<h1>Not Figure 4</h1>
{facts(d)}
<p class="note">
  Sharma &amp; Oberoi 2020 Figure 4 is a different scan the same morning:
  {FIG4_OBSID} at 03:39–03:44 UT, ten minutes earlier. The maps live on
  <a href="{FIG4_OBSID}.html">that page</a>, not here.
</p>
"""
    if d["obsid"] == "1133236216":
        return f"""
<p class="kicker">{e(fmt_date(d["date"]))} · one day after Figure 4</p>
<h1>The co-rotation test</h1>
{facts(d)}
<p>
  Same local time as Figure 4, 24.2 hours later. A compact feature that
  co-rotates with the Sun should shift about 150–200 arcsec westward.
  If it sits in the same place, it is the beam and the disk, not a source.
</p>
<div class="empty">CASA SuperUniform frames exist on the cluster. Mean brightness-temperature maps are running. They will appear here when the mean is on disk; nothing is shown until then.</div>
<p class="note"><a href="{FIG4_OBSID}.html">3 December, Figure 4 scan</a></p>
"""
    if d["obsid"] == "1111376776":
        return f"""
<p class="kicker">{e(fmt_date(d["date"]))} · a different season</p>
<h1>March, not December</h1>
{facts(d)}
<p>
  Same CASA recipe as Figure 4: 0.5 s Sun, 4 s 3C444, SuperUniform, Mohan
  conversion, mean of the scan. The P-angle is near zero this day, so solar
  north and celestial north almost coincide.
</p>
<div class="empty">Archive download submitted. Imaging starts when the measurement sets are Ready. This page stays empty until the maps exist.</div>
"""
    return f"""
<p class="kicker">{e(fmt_date(d["date"]))}</p>
<h1>Local noon</h1>
{facts(d)}
<div class="empty">Not imaged yet. This page is a place in the catalogue, not a map.</div>
"""


def day_page(d: dict, prev: dict | None, nxt: dict | None, media: dict[str, str]) -> str:
    return (
        head(f"{fmt_date(d['date'])} · Quiet Sun", root="..")
        + nav(root="..")
        + f'<main class="wrap">{day_body(d, media)}{pager_html(prev, nxt)}</main>'
        + foot()
    )


def fig4_page(media: dict[str, str], noon: dict | None) -> str:
    img = media.get("fig4_vs_paircars.png", "")
    img2 = media.get("fig4_his_vs_ours.png", "")
    back = f'o/{noon["obsid"]}.html' if noon else "index.html"
    return (
        head("3 December 2015 · Figure 4", root="..")
        + nav(root="..")
        + f"""<main class="wrap">
<p class="kicker">3 December 2015 · 03:39–03:44 UT</p>
<h1>Figure 4</h1>
<dl class="facts">
  <div><dt>Observation</dt><dd>{FIG4_OBSID}</dd></div>
  <div><dt>Start</dt><dd>{e(fmt_time(FIG4_START))}</dd></div>
  <div><dt>Length</dt><dd>296 s</dd></div>
  <div><dt>Noon pick that day</dt><dd><a href="{FIG4_NOON}.html">{FIG4_NOON}</a>, ten minutes later</dd></div>
  <div><dt>Calibrator</dt><dd>3C444 · 1133161488, for the P-AIRCARS column</dd></div>
</dl>
<p>
  All panels solar north up. Rohit’s CASA maps were celestial north; they
  are rotated by +15.4° (the P-angle that morning). P-AIRCARS is already
  solar north. Brightness temperature in million K.
</p>
<div class="figure"><img src="../{img}" alt="Rohit, our remake, P-AIRCARS self-cal, P-AIRCARS calibrator-only, four frequencies"></div>
<p class="caption">
  108 and 162 MHz: the disk is recovered in all four columns. Peak
  brightness temperatures at 108 MHz are 0.89, 0.89, 0.82 and 0.83 million K.
  At 162 MHz they are 0.99, 1.01, 0.88 and 0.90. At 217 and 240 MHz
  P-AIRCARS did not recover the disk; those panels are noise, not a
  quiet-Sun map.
</p>
<div class="figure"><img src="../{img2}" alt="Rohit versus our remake only"></div>
<p class="caption">
  Rohit’s maps and our remake of his CASA SuperUniform frames, same
  conversion, celestial north as in the FITS. This is the pair for Figure 4
  itself. P-AIRCARS is a different pipeline and is not mixed into that remake.
</p>
<div class="pager">
  <a href="../{back}">Noon pick that morning</a>
  <a href="../compare.html">All comparisons</a>
</div>
</main>
"""
        + foot()
    )


def compare_page(media: dict[str, str]) -> str:
    img = media.get("fig4_vs_paircars.png", "")
    img2 = media.get("fig4_his_vs_ours.png", "")
    return (
        head("Comparisons · Quiet Sun")
        + nav(current="compare")
        + f"""<main class="wrap">
<p class="kicker">What we can show</p>
<h1>Comparisons</h1>
<p class="lede">
  One quiet morning is fully mapped. The next day is on the cluster. A
  different season is still in the archive queue. That is the whole list.
</p>

<p class="kicker">3 December 2015 · 03:39 UT</p>
<h2 class="section">Figure 4, four ways</h2>
<p class="meta">
  Observation {FIG4_OBSID}, not the noon-catalogue pick that day.
  All panels solar north up. Brightness temperature, million K.
</p>
<div class="figure"><img src="{img}" alt="Rohit, our remake, P-AIRCARS self-cal, P-AIRCARS calibrator-only"></div>
<p class="caption">
  108 and 162 MHz: Rohit, our remake, and P-AIRCARS all recover the disk.
  Peak brightness temperatures agree to about ten percent at 108 MHz.
  At 162 MHz P-AIRCARS is fainter (0.88 against 0.99 million K).
  217 and 240 MHz: P-AIRCARS did not recover the disk. Those columns are
  shown because that is what the pipeline produced, not because they are
  quiet-Sun maps.
</p>
<div class="figure"><img src="{img2}" alt="Rohit versus our remake only"></div>
<p class="caption">
  Rohit’s maps and our remake of his CASA SuperUniform frames, same
  conversion. This is the honest pair for Figure 4 itself. P-AIRCARS is a
  different pipeline and is not mixed into that remake.
</p>
<p class="note">
  <a href="o/{FIG4_OBSID}.html">Figure 4 scan</a>
  · <a href="o/{FIG4_NOON}.html">3 December noon pick</a>
  · <a href="o/1133236216.html">4 December, co-rotation test</a>
  · <a href="o/1111376776.html">26 March 2015</a>
</p>
</main>
"""
        + foot()
    )


def about_page() -> str:
    now = datetime.now(timezone.utc).strftime("%-d %B %Y")
    return (
        head("About · Quiet Sun")
        + nav(current="about")
        + f"""<main class="wrap">
<p class="kicker">Catalogue</p>
<h1>What this site is</h1>
<p class="lede">
  A reading room for quiet-Sun maps from the Murchison Widefield Array,
  built from the 2013–2015 local-noon list. It is not a burst catalogue.
</p>
<p>
  A day is listed if GOES was quiet and the MWA observed the Sun within
  30 minutes of local noon. 238 of 305 days have a compact calibrator
  within 24 hours. Figure 4 of Sharma &amp; Oberoi (2020) is the 3 December
  2015 scan at 03:39 UT. That scan is not the noon pick in the table; the
  noon pick that day is ten minutes later.
</p>
<p>
  Brightness temperature is given in million K. We do not quote a 2022
  scale factor on these maps. The CASA path is SuperUniform snapshots,
  then the Mohan &amp; Oberoi conversion, then the mean of the scan.
  P-AIRCARS is shown beside that path, not inside it.
</p>
<p class="note">Pages generated {e(now)}. Empty days are waiting for maps, not errors.</p>
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
    write(SITE / "js/catalogue.js", catalogue_js())
    write(SITE / "index.html", index_page(days, media))
    write(SITE / "compare.html", compare_page(media))
    write(SITE / "about.html", about_page())
    noon = next((d for d in days if d["obsid"] == FIG4_NOON), None)
    write(SITE / "o" / f"{FIG4_OBSID}.html", fig4_page(media, noon))
    for i, d in enumerate(days):
        prev, nxt = neighbours(days, i)
        write(SITE / "o" / f'{d["obsid"]}.html', day_page(d, prev, nxt, media))
    print(f"wrote {len(days) + 1} observation pages under {SITE}")


if __name__ == "__main__":
    main()
