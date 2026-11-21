#!/usr/bin/env python3
"""Build the 30 September 2022 flare site.

Writes static HTML under site/flares/. Captions are numbers from the
maps we already have. Does not invent maps.
"""

from __future__ import annotations

import html
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site/flares"
MEDIA = SITE / "media"
FIG = ROOT / "figures/flare20220930"
CSS_SRC = ROOT / "site/quiet-sun/css/site.css"

FONT = (
    "https://fonts.googleapis.com/css2?"
    "family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&"
    "family=Source+Sans+3:wght@400;500;600&display=swap"
)

# name -> (filename in figures/flare20220930, alt, caption)
IMAGES = [
    (
        "1348545200_ch113_peak_hpc_aia.png",
        "M1.1 at 03:57 UT, MWA 144.6 MHz, AIA, STIX",
        "03:57:24 UT, 144.6 MHz. Radio source on AR 13110. M1.1 on the north-east limb is radio-quiet at this time. STIX 2209300352.",
    ),
    (
        "paircars_vs_hyperdrive_042844.png",
        "Type III at 04:28:44, hyperdrive and P-AIRCARS on AIA 193",
        "04:28:44 UT, 143.4 MHz, 4 s, AIA 193. Hyperdrive peak/rms 56; P-AIRCARS 3C444 only 70; P-AIRCARS self-cal 312. Positions agree.",
    ),
    (
        "paircars_burst_24ch_042844.png",
        "P-AIRCARS 24 channels at 04:28:42–46",
        "P-AIRCARS, 3C444 + self-cal, 04:28:42–46 UT, 4 s. 21 of 24 channels usable. Solar north up.",
    ),
    (
        "burst_height_vs_freq.png",
        "Type III height versus frequency",
        "04:28:36–44 UT. 19 channels with SNR > 50. Mean height 346″ ± 22″ ≈ 1.21 R☉.",
    ),
    (
        "pfss_ar13110.png",
        "PFSS from AR 13110 and MWA centroids",
        "PFSS (GONG 04:04 UT) from AR 13110. Open lines (green) 36, closed (white) 133. MWA centroids 04:28:36–44 sit on open field from the west edge of the region.",
    ),
    (
        "quiet_sun_ch107_compare.png",
        "137 MHz, two observations, two calibrators",
        "137.0 MHz. Left: 1348543720, 03:30–03:33, PKS0408-65, disk 0.36 MK, storm 9 MK. Right: 1348547272, 28 quietest of 136 × 2 s, 3C444, disk 0.43 MK, storm 85 MK. At 0.7–0.8 R☉ both ≈ 0.37 MK.",
    ),
    (
        "quiet_sun_ch116_fullobs.png",
        "148.5 MHz, 28 quietest frames of the burst observation",
        "1348547272, 148.5 MHz, mean of the 28 quietest of 136 × 2 s frames. Quiet disk 0.78 MK, radio-disk half radius 1.25 R☉. Storm over AR 13110 ≈ 86 MK.",
    ),
    (
        "paircars_burst_ch116_8steps.png",
        "P-AIRCARS 148.5 MHz, eight 4 s steps",
        "148.5 MHz, eight 4 s steps through the type III.",
    ),
    (
        "burst10_ch116_mwa_peak.png",
        "MWA 148.5 MHz peak of the 10 × 4 s sequence",
        "148.5 MHz, peak of the 10 × 4 s sequence.",
    ),
    (
        "burst10_ch116_aia_peak.png",
        "AIA 193 with MWA contours, 10 × 4 s peak",
        "AIA 193 with MWA 148.5 MHz contours at the peak of the 10 × 4 s sequence.",
    ),
    (
        "burst2s_ch116_mwa_peak.png",
        "MWA 148.5 MHz, 2 s peak",
        "148.5 MHz, 2 s imaging, peak frame.",
    ),
    (
        "burst2s_ch116_aia_peak.png",
        "AIA 193 with 2 s MWA contours",
        "AIA 193 with 2 s MWA 148.5 MHz contours.",
    ),
    (
        "burst025s_ch116_mwa_peak.png",
        "MWA 148.5 MHz, 0.25 s peak",
        "148.5 MHz, 0.25 s imaging, peak frame.",
    ),
    (
        "burst025s_ch116_aia_peak.png",
        "AIA 193 with 0.25 s MWA contours",
        "AIA 193 with 0.25 s MWA 148.5 MHz contours.",
    ),
    (
        "burst025s_ch116_significance.png",
        "0.25 s significance at 148.5 MHz",
        "0.25 s, 148.5 MHz, significance of the burst against the quiet frames.",
    ),
    (
        "paircars_burst2s_ch116.png",
        "P-AIRCARS 2 s at 148.5 MHz",
        "P-AIRCARS, 2 s, 148.5 MHz.",
    ),
    (
        "paircars_burst10_ch116.png",
        "P-AIRCARS 10 × 4 s at 148.5 MHz",
        "P-AIRCARS, 10 × 4 s, 148.5 MHz.",
    ),
]


def e(s: object) -> str:
    return html.escape(str(s), quote=True)


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


def nav(*, current: str = "") -> str:
    def item(href: str, label: str, key: str) -> str:
        if current == key:
            return f"<strong>{label}</strong>"
        return f'<a href="{href}">{label}</a>'

    return f"""<nav class="top wrap-wide">
  <div>{item("index.html", "Flares", "index")} · MWA · 30 September 2022</div>
  <div>
    {item("images.html", "Images", "images")}
    &ensp;{item("runs.html", "Runs", "runs")}
  </div>
</nav>
"""


def foot() -> str:
    return """<footer class="wrap-wide">
  30 September 2022. Brightness temperature in million K.
  <a href="https://github.com/i4Ds/mwa-quiet-sun">Quiet Sun</a> ·
  <a href="https://github.com/i4Ds/mwa-flares">Flares</a>
</footer>
</body>
</html>
"""


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def copy_media() -> list[str]:
    MEDIA.mkdir(parents=True, exist_ok=True)
    present = []
    for name, _alt, _cap in IMAGES:
        src = FIG / name
        if src.is_file():
            shutil.copy2(src, MEDIA / name)
            present.append(name)
    return present


def figure(name: str, alt: str, caption: str) -> str:
    return (
        f'<div class="figure"><img src="media/{name}" alt="{e(alt)}"></div>\n'
        f'<p class="caption">{caption}</p>\n'
    )


def index_page() -> str:
    thumb = "media/paircars_vs_hyperdrive_042844.png"
    m1 = "media/1348545200_ch113_peak_hpc_aia.png"
    hgt = "media/burst_height_vs_freq.png"
    return (
        head("30 September 2022 · MWA")
        + nav(current="index")
        + f"""<main class="wrap-wide">
<p class="kicker">Murchison Widefield Array</p>
<h1>30 September 2022</h1>
<p class="lede">M1.1 at 03:57 UT on the north-east limb. Type III at 04:28:44 UT from AR 13110.</p>
<dl class="facts">
  <div><dt>GOES</dt><dd>M1.1</dd></div>
  <div><dt>STIX</dt><dd>2209300352</dd></div>
  <div><dt>Early Sun</dt><dd>1348543720 · 03:30 UT</dd></div>
  <div><dt>M1.1 image</dt><dd>1348545200 · 03:57:24 UT</dd></div>
  <div><dt>Type III</dt><dd>1348547272 · 04:27:42–04:32:22 UT</dd></div>
  <div><dt>Calibrators</dt><dd>PKS0408-65 1348522216 · 3C444 1348574416</dd></div>
</dl>
<div class="featured">
  <a href="images.html">
    <p class="kicker">04:28:44 UT · 143.4 MHz</p>
    <h2>Type III</h2>
    <p>Hyperdrive, P-AIRCARS calibrator-only, P-AIRCARS self-cal. Peak/rms 56 / 70 / 312.</p>
    <img src="{thumb}" alt="">
  </a>
  <a href="images.html">
    <p class="kicker">03:57:24 UT · 144.6 MHz</p>
    <h2>M1.1</h2>
    <p>Radio source on AR 13110. Limb flare radio-quiet.</p>
    <img src="{m1}" alt="" style="object-position:center 40%">
  </a>
  <a href="images.html">
    <p class="kicker">04:28:36–44 UT</p>
    <h2>1.21 R☉</h2>
    <p>19 channels, 346″ ± 22″. Open PFSS from the west of AR 13110.</p>
    <img src="{hgt}" alt="" style="object-position:right center">
  </a>
</div>
</main>
"""
        + foot()
    )


def images_page(present: list[str]) -> str:
    blocks = ['<p class="kicker">30 September 2022</p><h1>Images</h1>\n']
    have = set(present)
    for name, alt, cap in IMAGES:
        if name in have:
            blocks.append(figure(name, alt, cap))
    return (
        head("Images · 30 September 2022")
        + nav(current="images")
        + f'<main class="wrap">{"".join(blocks)}</main>'
        + foot()
    )


def runs_page() -> str:
    return (
        head("Runs · 30 September 2022")
        + nav(current="runs")
        + """<main class="wrap-wide">
<p class="kicker">MWA</p>
<h1>Runs</h1>
<table class="days">
<thead><tr><th>Time</th><th>Observation</th><th>What</th><th>Result</th></tr></thead>
<tbody>
<tr>
  <td>03:30–03:33</td>
  <td class="mono">1348543720</td>
  <td>P-AIRCARS, 137.0 MHz, PKS0408-65 + self-cal, 176 s</td>
  <td>Disk 0.36 MK. Storm 9 MK. Radio-disk 1.45 R☉.</td>
</tr>
<tr>
  <td>03:57:24</td>
  <td class="mono">1348545200</td>
  <td>hyperdrive DI + wsclean, 144.6 MHz, 4 s, Sun-centred</td>
  <td>Source on AR 13110. M1.1 radio-quiet.</td>
</tr>
<tr>
  <td>04:27:42–04:32:22</td>
  <td class="mono">1348547272</td>
  <td>P-AIRCARS, 148.5 MHz, 136 × 2 s, 3C444 + self-cal</td>
  <td>Quietest 28 frames: disk 0.78 MK. Storm ≈ 86 MK.</td>
</tr>
<tr>
  <td>04:28:44</td>
  <td class="mono">1348547272</td>
  <td>hyperdrive + wsclean vs P-AIRCARS, 143.4 MHz, 4 s</td>
  <td>Peak/rms 56 / 70 / 312. Positions agree.</td>
</tr>
<tr>
  <td>04:28:42–46</td>
  <td class="mono">1348547272</td>
  <td>P-AIRCARS, 24 coarse channels, 4 s</td>
  <td>21 usable. Height 346″ ± 22″ ≈ 1.21 R☉ (19 channels, SNR &gt; 50).</td>
</tr>
<tr>
  <td>04:28</td>
  <td class="mono">1348547272</td>
  <td>10 × 4 s, 2 s, and 0.25 s at 148.5 MHz</td>
  <td>Maps and AIA overlays on disk.</td>
</tr>
</tbody>
</table>
<p class="note">Calibrators: PKS0408-65 1348522216 (early), 3C444 1348574416 (burst).</p>
</main>
"""
        + foot()
    )


def main() -> None:
    SITE.mkdir(parents=True, exist_ok=True)
    (SITE / "css").mkdir(exist_ok=True)
    shutil.copy2(CSS_SRC, SITE / "css/site.css")
    present = copy_media()
    write(SITE / ".nojekyll", "")
    write(
        SITE / "README.md",
        "# Flares\n\n"
        "Private i4Ds repo. MWA flare maps, 30 September 2022. "
        "Brightness temperature in million K.\n\n"
        "Quiet Sun: [i4Ds/mwa-quiet-sun](https://github.com/i4Ds/mwa-quiet-sun).\n\n"
        "Generated from [i4Ds/solar-burst-multiview]"
        "(https://github.com/i4Ds/solar-burst-multiview):\n\n"
        "```\npython3 scripts/flare_site.py\n```\n",
    )
    write(SITE / "index.html", index_page())
    write(SITE / "images.html", images_page(present))
    write(SITE / "runs.html", runs_page())
    print(f"wrote {len(present)} images under {SITE}")


if __name__ == "__main__":
    main()
