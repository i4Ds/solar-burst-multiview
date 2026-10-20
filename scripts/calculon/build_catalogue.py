#!/usr/bin/env python3
"""Catalogue page of the archive-burst images from MLflow (experiment "archive-bursts").

Writes OUT/index.html and OUT/img/*.png: a sortable table of all runs (date, burst type,
phase, frequency, peak/rms, position, T_B, status) and one card per image with the
image figure (Stonyhurst grid), the MWA light curve and the context figure (GOES, STIX,
e-Callisto), the key numbers and the run description. The page is published as an
Artifact from the Mac (copy OUT over first).

    ~/mwa/mlflow-venv/bin/python ~/mwa/events/build_catalogue.py --out ~/mwa/catalogue
"""
import argparse
import html
import os
import re
import shutil

HOME = os.path.expanduser("~")
STORE = f"sqlite:///{HOME}/mwa/mlflow/mlflow.db"


def esc(x):
    return html.escape("" if x is None else str(x))


def md_inline(s):
    """The few Markdown bits the run descriptions use: **bold**, `code`, line breaks."""
    s = esc(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"`(.+?)`", r"<code>\1</code>", s)
    out, items = [], []
    for line in s.splitlines():
        if line.startswith("- "):
            items.append(f"<li>{line[2:]}</li>")
            continue
        if items:
            out.append("<ul>" + "".join(items) + "</ul>")
            items = []
        if line.strip():
            out.append(f"<p>{line}</p>")
    if items:
        out.append("<ul>" + "".join(items) + "</ul>")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=f"{HOME}/mwa/catalogue")
    a = ap.parse_args()
    import mlflow
    mlflow.set_tracking_uri(STORE)
    runs = mlflow.search_runs(experiment_names=["archive-bursts"], output_format="list",
                              order_by=["params.image_time ASC"])
    os.makedirs(f"{a.out}/img", exist_ok=True)
    rows, cards = [], []
    for n, r in enumerate(runs, 1):
        p, m, t = r.data.params, r.data.metrics, r.data.tags
        art = r.info.artifact_uri.replace("file://", "")
        pics = {}
        for f in sorted(os.listdir(art)) if os.path.isdir(art) else []:
            kind = ("grid" if f.endswith("_grid.png") else "lc" if f.endswith("_lightcurve.png")
                    else "ctx" if f.startswith("context_") and f.endswith("_zoom.png") else None)
            if kind:
                dst = f"img/{r.info.run_id[:8]}_{kind}.png"
                shutil.copy(f"{art}/{f}", f"{a.out}/{dst}")
                pics[kind] = dst
        status = t.get("status", "ok")
        when = p.get("image_time", "")
        rows.append(f"""<tr data-status="{esc(status)}">
<td data-v="{esc(when)}"><a href="#r{n}">{esc(when[:10])}</a></td><td class="mono">{esc(when[11:21])}</td>
<td>{esc(t.get('burst_type', ''))}</td><td>{esc(t.get('phase', ''))}</td><td>{esc(t.get('project', ''))}</td>
<td class="num">{float(p.get('freq_mhz', 0)):.1f}</td>
<td class="num" data-v="{m.get('peak_over_rms', 0):.3f}">{m.get('peak_over_rms', 0):.0f}</td>
<td class="num" data-v="{m.get('peak_jy_beam', 0):.6g}">{m.get('peak_jy_beam', 0):.2g}</td>
<td class="num mono">({m.get('x_arcsec', 0):.0f}, {m.get('y_arcsec', 0):.0f})</td>
<td class="num" data-v="{m.get('r_rsun', 0):.4f}">{m.get('r_rsun', 0):.2f}</td>
<td class="num" data-v="{m.get('tb_rj_k', 0):.6g}">{m.get('tb_rj_k', 0):.1e}</td>
<td><span class="pill {esc(status)}">{esc(status)}</span></td></tr>""")
        figs = "".join(f'<figure><a href="{pics[k]}" target="_blank" rel="noopener"><img loading="lazy" src="{pics[k]}" alt="{cap}"></a><figcaption>{cap}</figcaption></figure>'
                       for k, cap in [("grid", "MWA image, Stonyhurst grid 15°"), ("lc", "MWA light curve, chosen 4 s"),
                                      ("ctx", "GOES, STIX, e-Callisto, MWA")] if k in pics)
        cards.append(f"""<article class="card" id="r{n}">
<header><h3>{esc(t.get('mlflow.runName', when))}</h3><span class="pill {esc(status)}">{esc(status)}</span></header>
<div class="figs">{figs}</div>
<div class="desc">{md_inline(t.get('mlflow.note.content', ''))}</div>
<p class="meta">MWA {esc(p.get('obsid'))} · calibrator {esc(p.get('calibrator'))} · channel {esc(p.get('coarse_channel'))} ·
{esc(p.get('pipeline'))} · {esc(p.get('birli'))} · commit <code>{esc(p.get('sbm_commit'))}</code> · MLflow run <code>{r.info.run_id[:8]}</code></p>
</article>""")
    n_ok = sum(1 for r in runs if r.data.tags.get("status", "ok") == "ok")
    page = TEMPLATE.format(n=len(runs), n_ok=n_ok, n_check=len(runs) - n_ok, rows="\n".join(rows),
                           cards="\n".join(cards))
    open(f"{a.out}/index.html", "w").write(page)
    print(f"{len(runs)} runs -> {a.out}/index.html")


TEMPLATE = """<title>MWA Burst Images</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&family=Fraunces:opsz,wght@9..144,600&display=swap">
<style>
/* Layout: an observing log. Summary line, a sortable table of all images, then one card per image. */
:root {{
  --bg: #f6f7f9; --surface: #ffffff; --fg: #18202b; --muted: #5a6573; --line: #dde2e8;
  --accent: #1c5cab; --ok: #1f7a4d; --check: #9a5b00; --bad: #b3261e; --chip: #eef2f7;
  --display: "Fraunces", Georgia, serif; --body: "IBM Plex Sans", system-ui, sans-serif;
  --mono: "IBM Plex Mono", ui-monospace, monospace;
}}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{
  --bg: #11161d; --surface: #19202a; --fg: #e6ebf1; --muted: #9aa6b4; --line: #2a3441;
  --accent: #7fb0ec; --ok: #5fc896; --check: #e3a64a; --bad: #f2867c; --chip: #232c38; color-scheme: dark }} }}
:root[data-theme="dark"] {{
  --bg: #11161d; --surface: #19202a; --fg: #e6ebf1; --muted: #9aa6b4; --line: #2a3441;
  --accent: #7fb0ec; --ok: #5fc896; --check: #e3a64a; --bad: #f2867c; --chip: #232c38; color-scheme: dark }}
body {{ background: var(--bg); color: var(--fg); font-family: var(--body); line-height: 1.5; }}
main {{ max-width: 1320px; margin: 0 auto; padding-inline: 20px; padding-block: 28px 64px; display: grid; gap: 28px; }}
h1 {{ font-family: var(--display); font-size: clamp(1.7rem, 3vw, 2.3rem); margin: 0; text-wrap: balance; }}
h2 {{ font-family: var(--display); font-size: 1.35rem; margin: 0; }}
h3 {{ font-size: 1.02rem; margin: 0; font-weight: 600; }}
.intro {{ display: grid; gap: 8px; max-width: 75ch; }}
.intro p {{ margin: 0; color: var(--muted); }}
.stats {{ display: flex; flex-wrap: wrap; gap: 8px 28px; font-variant-numeric: tabular-nums; }}
.stats div {{ display: grid; }}
.stats b {{ font-family: var(--mono); font-size: 1.35rem; font-weight: 500; }}
.stats span {{ font-size: .78rem; text-transform: uppercase; letter-spacing: .06em; color: var(--muted); }}
.tablewrap {{ overflow-x: auto; border: 1px solid var(--line); border-radius: 8px; background: var(--surface); }}
table {{ border-collapse: collapse; width: 100%; font-size: .88rem; font-variant-numeric: tabular-nums; }}
th, td {{ padding: 7px 10px; border-bottom: 1px solid var(--line); text-align: left; white-space: nowrap; }}
th {{ font-weight: 600; color: var(--muted); font-size: .76rem; text-transform: uppercase; letter-spacing: .05em; cursor: pointer; user-select: none; }}
th[aria-sort="ascending"]::after {{ content: " ▲"; }} th[aria-sort="descending"]::after {{ content: " ▼"; }}
tr:last-child td {{ border-bottom: 0; }}
td.num {{ text-align: right; }} .mono, code {{ font-family: var(--mono); font-size: .92em; }}
a {{ color: var(--accent); }} a:focus-visible, th:focus-visible {{ outline: 2px solid var(--accent); outline-offset: 2px; }}
.pill {{ font-size: .72rem; padding: 2px 9px; border-radius: 99px; background: var(--chip); font-weight: 600; letter-spacing: .03em; }}
.pill.ok {{ color: var(--ok); }} .pill.check {{ color: var(--check); }} .pill.bad {{ color: var(--bad); }}
.cards {{ display: grid; gap: 18px; }}
.card {{ background: var(--surface); border: 1px solid var(--line); border-radius: 8px; padding: 16px; display: grid; gap: 12px; min-width: 0; }}
.card header {{ display: flex; gap: 12px; align-items: baseline; flex-wrap: wrap; }}
.figs {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 300px), 1fr)); gap: 12px; align-items: start; }}
figure {{ margin: 0; display: grid; gap: 4px; min-width: 0; }}
figure img {{ width: 100%; height: auto; border-radius: 4px; background: #fff; display: block; }}
figcaption {{ font-size: .78rem; color: var(--muted); }}
.desc {{ max-width: 90ch; font-size: .92rem; }} .desc p, .desc ul {{ margin: 0 0 6px; }}
.meta {{ margin: 0; font-size: .8rem; color: var(--muted); }}
</style>
<main>
  <div class="intro">
    <h1>MWA burst images</h1>
    <p>One MWA image per solar radio burst: 4 s at the maximum of the MWA light curve, 162.5 MHz unless noted,
    P-AIRCARS self-calibration, Stokes I, no AOFlagger. Built from the MLflow experiment “archive-bursts” on calculon.
    Status “check” means something is still to be verified; see the card.</p>
    <div class="stats"><div><b>{n}</b><span>images</span></div><div><b>{n_ok}</b><span>ok</span></div>
    <div><b>{n_check}</b><span>to check</span></div></div>
  </div>
  <section>
    <div class="tablewrap"><table id="t">
      <thead><tr><th>date</th><th>start UTC</th><th>type</th><th>phase</th><th>project</th><th>MHz</th>
      <th>peak/rms</th><th>peak Jy/beam</th><th>position ″</th><th>r R☉</th><th>T_B K</th><th>status</th></tr></thead>
      <tbody>{rows}</tbody>
    </table></div>
  </section>
  <section class="cards">{cards}</section>
</main>
<script>
const t = document.getElementById("t");
t.querySelectorAll("th").forEach((th, i) => {{
  th.tabIndex = 0;
  const sort = () => {{
    const dir = th.getAttribute("aria-sort") === "ascending" ? -1 : 1;
    t.querySelectorAll("th").forEach(h => h.removeAttribute("aria-sort"));
    th.setAttribute("aria-sort", dir === 1 ? "ascending" : "descending");
    const rows = [...t.tBodies[0].rows];
    const key = r => {{ const c = r.cells[i]; const v = c.dataset.v ?? c.textContent.trim();
      const x = parseFloat(v); return isNaN(x) || /^\\d{{4}}-/.test(v) ? v : x; }};
    rows.sort((a, b) => {{ const x = key(a), y = key(b); return (x > y ? 1 : x < y ? -1 : 0) * dir; }});
    rows.forEach(r => t.tBodies[0].appendChild(r));
  }};
  th.addEventListener("click", sort);
  th.addEventListener("keydown", e => {{ if (e.key === "Enter" || e.key === " ") {{ e.preventDefault(); sort(); }} }});
}});
</script>
"""

if __name__ == "__main__":
    main()
