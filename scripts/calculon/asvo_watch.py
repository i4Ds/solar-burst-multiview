#!/usr/bin/env python3
"""Decide which ASVO jobs to download (called by asvo-watch.sbatch every 30 min).

stdin: `giant-squid list --json`. Args: DEST MAXDL RUNNING_FILE STATUS_FILE, where
RUNNING_FILE lists the Slurm job names in the queue (asvo-dl-<jobid>).
stdout: one line per download to start, "DL <jobid> <obsid> <kind> <bytes>", then
"PENDING <n>" (jobs not yet Ready plus downloads not finished). A Ready job is
downloaded when its tar is not on the NAS with the full size and no asvo-dl job runs
for it; at most MAXDL large downloads run at once, plus up to SMALL_SLOTS jobs under
SMALL_BYTES (calibrators of a few GB), so these are not stuck behind 1 TB raw tars
(23 Oct: three 0.9-1.1 TB batch-2 tars blocked every calibrator for 9 h). Writes a
readable status table.
"""
import json
import os
import sys
import time

dest, maxdl, running_file, status_file = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4]
raw = sys.stdin.read()
jobs = json.loads(raw[raw.index("{"):]) if "{" in raw else {}
SMALL_BYTES, SMALL_SLOTS = 100e9, 2
running = {l.strip() for l in open(running_file) if l.strip()}


def nbytes(j):
    return sum(f.get("fileSize") or 0 for f in (j.get("files") or []))


n_running = {"large": 0, "small": 0}
for j in jobs.values():
    if f"asvo-dl-{j['jobId']}" in running:
        n_running["small" if nbytes(j) < SMALL_BYTES else "large"] += 1
slots = {"large": maxdl, "small": SMALL_SLOTS}
pending, rows = 0, []
for j in sorted(jobs.values(), key=lambda j: j["jobId"]):
    kind = "vis" if j["jobType"] == "DownloadVisibilities" else "ms"
    tar = os.path.join(dest, f"{j['obsid']}_{j['jobId']}_{kind}.tar")
    size = os.path.getsize(tar) if os.path.exists(tar) else 0
    want = nbytes(j)
    pool = "small" if want < SMALL_BYTES else "large"
    state = j["jobState"]
    if state == "Ready":
        if want and size >= want:
            local = "on NAS"
        elif f"asvo-dl-{j['jobId']}" in running:
            local, pending = f"downloading {size / 1e9:.1f}/{want / 1e9:.1f} GB", pending + 1
        elif n_running[pool] < slots[pool]:
            print(f"DL {j['jobId']} {j['obsid']} {kind} {want}")
            n_running[pool] += 1
            local, pending = "download started", pending + 1
        else:
            local, pending = "waiting for a download slot", pending + 1
    elif state in ("Error", "Expired", "Cancelled"):
        local = "nothing to do (ASVO " + state + ")"
    else:
        local, pending = "waiting for ASVO", pending + 1
    rows.append(f"{j['jobId']:>8} {j['obsid']:>11} {kind:4} {state:22} {local}")
print(f"PENDING {pending}")
with open(status_file, "w") as f:
    f.write(f"# ASVO watch {time.strftime('%Y-%m-%d %H:%M:%S %Z')}, pending {pending}\n")
    f.write("\n".join(rows) + "\n")
