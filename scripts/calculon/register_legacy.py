#!/usr/bin/env python3
"""One-off (22 Oct 2026): enter the images made with event_image.sh into the product registry
(~/mwa/products/<SUN>_ch<CH>_peak4s.json, "legacy": true) and write the event table
~/mwa/products/events.json from the batch lists' tags. Legacy entries keep reading their state
from ~/mwa/events/<SUN>.md, so runs still going under event_image.sh are picked up by the export.
"""
import glob
import json
import os
import re

H = os.path.expanduser("~")
EV, PR = f"{H}/mwa/events", f"{H}/mwa/products"
os.makedirs(PR, exist_ok=True)

lines = {}
for f in sorted(glob.glob(f"{EV}/batch*.txt")) + sorted(glob.glob(f"{EV}/rerun*.txt")):
    if os.path.basename(f) == "batch2a.txt":
        continue
    for ln in open(f):
        if ln.strip() and not ln.startswith("#"):
            lines[ln.split()[0]] = ln.split()     # later lists override earlier ones
lines["1419137296"] = ("1419137296 1114407 1419161128 1114408 20241225 --tag burst_type=II --tag phase=III "
                       "--tag project=OA004 --tag tier=A").split()

events = json.load(open(f"{PR}/events.json")) if os.path.exists(f"{PR}/events.json") else {}
for sun, f in lines.items():
    sun_job, cal, cal_job, datedir = f[1:5]
    rest = f[5:]
    ch = "127"
    if rest and rest[0].startswith("CH="):
        ch, rest = rest[0][3:], rest[1:]
    tags = dict(t.split("=", 1) for t in rest[1::2] if "=" in t)
    ev = events.setdefault(sun, {})
    ev.update({k: v for k, v in tags.items() if k != "channel_note"})
    md = f"{EV}/{sun}.md"
    hdr = open(md).readline() if os.path.exists(md) else ""
    m = re.search(r"ch (\d+), calibrator (\d+)", hdr)
    if m:
        ch, cal = m.group(1), m.group(2)
    prod = f"{sun}_ch{ch}_peak4s"
    entry = dict(product=prod, sun=sun, sun_job=sun_job, cal=cal, cal_job=cal_job, ch=ch, datedir=datedir,
                 label="peak4s", tres="4", tag=f"{sun}_ch{ch}", legacy=True, legacy_md=md,
                 note=tags.get("channel_note", "").replace("_", " "), attempts=[])
    json.dump(entry, open(f"{PR}/{prod}.json", "w"), indent=1)
    print(prod, cal, datedir)

events.setdefault("1419137296", {}).update(
    flare="GOES M4.9, AR 13932 (peak 04:49)",
    note="Flat-topped light-curve maxima: possible clipping, not checked. MWA starts 04:47:58, after the "
         "hard X-ray peak and the broadband burst.",
    marks=[[5.7, -188.1, "AR 13932"], [-88, -297, "STIX flare"]],
    context=f"{EV}/context_1419137296_zoom.png")
json.dump(events, open(f"{PR}/events.json", "w"), indent=1)
print(len(events), "events")
