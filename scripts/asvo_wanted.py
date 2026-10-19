#!/usr/bin/env python
"""Wanted list for ASVO from the e-Callisto candidates (i4Ds/STIX-MWA, _results/ecallisto_mwa_bursts).

Targets are requested as raw visibilities (`vis`): the whole observation once, every
later product made with Birli on calculon (no AOFlagger). Calibrators are requested
as one ASVO conversion each, all channels, 2 s / 160 kHz, no AOFlagger
(`obsstore.CONV_PARAMS`), because their raw archives are ~0.5 TB each.

Batches: 0 = 2024-12-25 type II (1419137296), the end-to-end test; 1 = Phase IIIb
events shown in the review gallery; 2 = tier A events of earlier phases.

    python scripts/asvo_wanted.py ~/Projects/STIX-MWA/_results/ecallisto_mwa_bursts \
        --out configs/asvo/wanted-2026-10.csv
"""

import argparse
from pathlib import Path

import pandas as pd

from solarburst.obsstore import CONV_PARAMS

FIXED_CHANNEL = 127   # 162.6 MHz, in the standard G0002 picket fence
BATCH0 = 1419137296


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("results", type=Path, help="STIX-MWA _results/ecallisto_mwa_bursts")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--sizes", type=Path, nargs="*", default=[],
                    help="CSVs with obs_id and total_archived_data_bytes (mwa_sun_obs.csv, calibrators.csv)")
    args = ap.parse_args()

    c = pd.read_csv(args.results / "candidates.csv", parse_dates=["t_peak"])
    p = pd.read_csv(args.results / "pictures" / "proposals.csv", parse_dates=["t_peak"])
    c = c.merge(p[["mwa_obs_id", "t_peak"]], on=["mwa_obs_id", "t_peak"])   # the reviewed set
    c["batch"] = None
    c.loc[c.mwa_obs_id == BATCH0, "batch"] = 0
    c.loc[c.batch.isna() & c.phase3b, "batch"] = 1
    c.loc[c.batch.isna() & (c.tier == "A"), "batch"] = 2
    c = c[c.batch.notna()].drop_duplicates("mwa_obs_id")

    rows = []
    for r in c.itertuples():
        chans = str(r.mwa_channel_numbers_csv).split(",")
        rows.append(dict(obsid=r.mwa_obs_id, kind="vis", params="", role="target", batch=int(r.batch),
                         event_utc=f"{r.t_peak:%Y-%m-%d %H:%M:%S}", tier=r.tier, phase=r.phase,
                         has_ch127=str(FIXED_CHANNEL) in chans,
                         note="" if pd.notna(r.cal_obs_id) else "no same-channel calibrator within 24 h"))
        if pd.notna(r.cal_obs_id):
            rows.append(dict(obsid=int(r.cal_obs_id), kind="ms", params=CONV_PARAMS, role="calibrator",
                             batch=int(r.batch), event_utc=f"{r.t_peak:%Y-%m-%d %H:%M:%S}", tier=r.tier,
                             phase=r.phase, has_ch127=str(FIXED_CHANNEL) in chans,
                             note=f"for {r.mwa_obs_id}; {str(r.cal_name).split('_Ch')[0]}, {r.cal_dt_hr} h"))
    w = pd.DataFrame(rows).sort_values(["batch", "role", "event_utc"], ascending=[True, False, True])
    # a calibrator shared by several events is requested once, in its first batch
    w = w.drop_duplicates(["obsid", "kind"], keep="first")
    sizes = pd.concat([pd.read_csv(f, usecols=["obs_id", "total_archived_data_bytes"]) for f in args.sizes]
                      or [pd.DataFrame(columns=["obs_id", "total_archived_data_bytes"])])
    sizes = sizes.drop_duplicates("obs_id").set_index("obs_id").total_archived_data_bytes
    w["bytes"] = w.obsid.map(sizes)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    w.to_csv(args.out, index=False)
    print(w.groupby(["batch", "role"]).agg(n=("obsid", "size"), TB=("bytes", lambda b: round(b.sum() / 1e12, 2)))
          .to_string())


if __name__ == "__main__":
    main()
