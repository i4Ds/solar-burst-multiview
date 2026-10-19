"""One registry of the MWA data on calculon, so no observation is requested from ASVO twice.

Three files under `configs/`, all versioned:

- `calculon_obs.csv`  the registry: every ASVO tar on the calculon NAS
  (`<obsid>_[<label>_]<asvojob>_<kind>.tar`), from one `ls` of the data dirs.
- `asvo_jobs.csv`     the ledger: every ASVO job we plan or submit, with its state
  (planned, submitted, ready, downloaded, failed, embargoed, on_hold). A job in
  flight counts as data we have, so it is never requested again; embargoed
  (MWA data are restricted to the PI for 18 months, `public_release_date_utc`
  in mwa.observation) and on_hold rows are not requested either.
- `asvo/wanted-*.csv` what we want: obsid, product, role, batch.

Products. `vis` is the raw archive (all channels, all time steps, correlator
resolution) and covers every later product: channels and averaging are chosen
when Birli runs on calculon (`scripts/calculon/raw-birli.sbatch`). `ms` is an
ASVO conversion with the parameters in `params`. An `ms` tar whose parameters we
do not know (older downloads) never counts as a match: it may have AOFlagger on.

    python -m solarburst.obsstore scan                       # needs the FHNW VPN
    python -m solarburst.obsstore scan --from-listing ls.txt # from a saved `ls -l`
    python -m solarburst.obsstore plan configs/asvo/wanted-2026-10.csv
    python -m solarburst.obsstore plan ... --write-ledger    # record the requests as "planned"
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

import pandas as pd

from solarburst.stage import _ssh_command

REPO = Path(__file__).resolve().parents[2]
REGISTRY = REPO / "configs" / "calculon_obs.csv"
LEDGER = REPO / "configs" / "asvo_jobs.csv"
DATA_DIRS = ["/mnt/nas05/data02/MWA_data/data/mwa_data", "/mnt/nas05/data02/MWA_data/data/mwa_data2"]
DOWNLOAD_DIR = DATA_DIRS[1]
LEDGER_COLS = ["obsid", "kind", "params", "role", "batch", "asvo_job", "state", "requested", "tar", "note"]
# validated on 1348547272 (docs/asvo-request-1348547272.md); AOFlagger off for every product
CONV_PARAMS = "output=ms,avg_time_res=2,avg_freq_res=160,flag_edge_width=80,no_rfi=true"

TAR = re.compile(r"^(?P<obsid>\d{10})_(?:(?P<label>[A-Za-z][\w-]*)_)?(?P<job>\d+)_(?P<kind>\w+)\.tar$")


def parse_listing(text: str) -> pd.DataFrame:
    """Rows from `ls -l` (with sizes) or plain `ls` output; lines naming a directory set its path."""
    rows, d = [], ""
    for line in text.splitlines():
        line = line.strip()
        if line.endswith(":"):
            d = line[:-1]
            continue
        parts = line.split()
        if not parts:
            continue
        m = TAR.match(parts[-1])
        if not m:
            continue
        size = int(parts[4]) if len(parts) >= 9 and parts[4].isdigit() else None
        rows.append(dict(obsid=int(m["obsid"]), kind=m["kind"], label=m["label"] or "",
                         asvo_job=int(m["job"]), bytes=size, path=f"{d}/{parts[-1]}" if d else parts[-1]))
    return pd.DataFrame(rows, columns=["obsid", "kind", "label", "asvo_job", "bytes", "path"])


def cmd_scan(args) -> None:
    if args.from_listing:
        text = Path(args.from_listing).read_text()
        listed = args.listed or "unknown"
    else:
        cmd = _ssh_command() + ["calculon", "ls -l " + " ".join(DATA_DIRS)]
        text = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
        listed = date.today().isoformat()
    reg = parse_listing(text).sort_values(["obsid", "kind", "asvo_job"])
    reg["listed"] = listed
    reg.to_csv(REGISTRY, index=False)
    print(f"{len(reg)} tars, {reg.obsid.nunique()} obsids -> {REGISTRY.relative_to(REPO)}", file=sys.stderr)


def read_ledger() -> pd.DataFrame:
    if LEDGER.exists():
        return pd.read_csv(LEDGER, dtype={"asvo_job": "Int64"}, keep_default_na=False)
    return pd.DataFrame(columns=LEDGER_COLS)


def covers(have_kind: str, have_params: str, want_kind: str, want_params: str) -> bool:
    """Does an existing product make a new request unnecessary?"""
    if have_kind == "vis":
        return True
    return have_kind == want_kind == "ms" and bool(have_params) and have_params == want_params


def status(want: pd.DataFrame, reg: pd.DataFrame, led: pd.DataFrame) -> pd.DataFrame:
    out = []
    for w in want.itertuples():
        params = w.params if isinstance(w.params, str) else ""
        hit = None
        for r in reg[reg.obsid == w.obsid].itertuples():
            # params of NAS tars are known only through the ledger
            p = led.loc[(led.asvo_job.astype(str) == str(r.asvo_job)), "params"]
            if covers(r.kind, p.iloc[0] if len(p) else "", w.kind, params):
                hit = ("have", r.path)
                break
        if hit is None:
            live = led[(led.obsid == w.obsid) & led.state.isin(["submitted", "ready", "downloaded"])]
            for r in live.itertuples():
                if covers(r.kind, r.params, w.kind, params):
                    hit = (f"ledger:{r.state}", f"asvo job {r.asvo_job}" if str(r.asvo_job) else "")
                    break
        if hit is None:
            # embargoed (ASVO error 999, data restricted to the PI) or deliberately held back
            held = led[(led.obsid == w.obsid) & led.state.isin(["embargoed", "on_hold"])]
            # during the embargo, open-access (OA...) data go to the PI only; collaboration
            # projects (e.g. G0002) are open to MWA collaboration members
            rel = getattr(w, "public_release_date_utc", "")
            oa = str(getattr(w, "projectid", "")).startswith("OA")
            if len(held):
                hit = (held.state.iloc[0], held.note.iloc[0])
            elif oa and isinstance(rel, str) and rel and pd.Timestamp(rel) > pd.Timestamp.now(tz="UTC"):
                hit = ("embargoed", f"open-access project, public from {rel[:10]}")
        if hit is None and len(led[(led.obsid == w.obsid) & (led.state == "planned")]):
            hit = ("planned", "in the ledger, not yet submitted")
        if hit is None:
            other = reg[reg.obsid == w.obsid]
            note = ("on calculon only as " + ", ".join(sorted(set(other.kind))) + " (params unknown)") if len(other) else ""
            hit = ("request", note)
        out.append(dict(w._asdict(), state=hit[0], where=hit[1]))
    return pd.DataFrame(out).drop(columns="Index")


def submit_lines(req: pd.DataFrame, chunk: int, local: bool = False) -> list[str]:
    """sbatch lines for scripts/calculon/asvo-submit-retry.sbatch, at most `chunk` obsids per job;
    with `local`, plain giant-squid commands for a shell that has MWA_ASVO_API_KEY set."""
    lines = []
    if local:   # one obsid per call, so an obs ASVO refuses (e.g. embargo) does not stop the others
        chunk = 1
    for batch, gb in req.groupby("batch", sort=True):
        tb = gb.bytes.sum() / 1e12 if "bytes" in gb else float("nan")
        lines.append(f"# batch {batch}: {len(gb)} obs, {tb:.2f} TB in the archive (conversions come out smaller)")
        for (kind, params), g in gb.groupby(["kind", "params"], dropna=False, sort=False):
            ids = [str(o) for o in g.obsid]
            for i in range(0, len(ids), chunk):
                part = " ".join(ids[i:i + chunk])
                if local:
                    cmd = (f"giant-squid submit-vis {part}" if kind == "vis" else
                           f"giant-squid submit-conv -p {params} {part}")
                    lines.append(f"{cmd} || failed+=({part})")
                    continue
                env =f"ALL,SUBMIT={'vis' if kind == 'vis' else 'conv'},OBSIDS='{part}'"
                if kind != "vis":
                    env += f",PARAMS='{params}'"
                lines.append(f"sbatch -M calc-cpu --export={env} ~/mwa/asvo-submit-retry.sbatch")
    return lines


def cmd_plan(args) -> None:
    want = pd.read_csv(args.wanted, keep_default_na=False)
    want["params"] = [p if k != "vis" else "" for k, p in zip(want.kind, want.params)]
    reg = pd.read_csv(REGISTRY) if REGISTRY.exists() else parse_listing("")
    led = read_ledger()
    st = status(want, reg, led)
    if args.batch:
        st = st[st.batch.astype(str).isin(args.batch.split(","))]
    pd.set_option("display.width", 200)
    print(st[["batch", "role", "obsid", "kind", "state", "where"]].to_string(index=False))
    req = st[st.state.isin(["request", "planned"])]
    print(f"\n{len(st)} wanted, {len(st) - len(req)} covered or held, {len(req)} to submit", file=sys.stderr)
    if req.empty:
        return
    lines = submit_lines(req, args.chunk, args.local)
    if args.local:
        lines = (["#!/bin/bash",
                  "# ASVO submissions, one obsid per call; a refused obsid is reported and skipped.",
                  "# Needs MWA_ASVO_API_KEY. Paste the final list back so the job ids go into configs/asvo_jobs.csv.",
                  ': "${MWA_ASVO_API_KEY:?set MWA_ASVO_API_KEY}"', "failed=()"] + lines +
                 ['echo; echo "not submitted (${#failed[@]}): ${failed[*]:-none}"', "giant-squid list"])
    else:
        lines = ["# submit (on calculon, API key from ~/.config/mwa_asvo/api_key):"] + lines
    text = "\n".join(lines) + "\n"
    if args.out:
        Path(args.out).write_text(text)
        print(f"-> {args.out}", file=sys.stderr)
    else:
        print("\n" + text)
    req = req[req.state == "request"]   # only rows not yet in the ledger are added
    if args.write_ledger and len(req):
        new = req.assign(asvo_job="", state="planned", requested=date.today().isoformat(), tar="",
                         note=req.get("note", ""))[LEDGER_COLS]
        pd.concat([led, new], ignore_index=True).to_csv(LEDGER, index=False)
        print(f"{len(new)} rows added to {LEDGER.relative_to(REPO)} as planned", file=sys.stderr)


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("scan", help="list the ASVO tars on calculon into the registry")
    a.add_argument("--from-listing", help="saved output of `ls -l DIR...` instead of ssh")
    a.add_argument("--listed", help="date of that listing (YYYY-MM-DD)")
    a.set_defaults(func=cmd_scan)
    a = sub.add_parser("plan", help="what of a wanted list still has to be requested")
    a.add_argument("wanted")
    a.add_argument("--batch", help="only these batches, comma separated")
    a.add_argument("--chunk", type=int, default=5, help="obsids per ASVO submission")
    a.add_argument("--write-ledger", action="store_true")
    a.add_argument("--local", action="store_true", help="giant-squid commands instead of sbatch lines")
    a.add_argument("--out", help="write the commands to this file")
    a.set_defaults(func=cmd_plan)
    args = ap.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
