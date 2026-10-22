#!/bin/bash
# Start one round of image products on calculon (22 Oct 2026): ASVO requests, download
# watcher, and the product lists; everything else waits for its data by itself.
#   bash ~/mwa/events/start_round.sh          (login node; returns at once)
# 1. ASVO: batch 2 targets (raw) and calibrators (conversion, no_rfi=true, 2 s, 160 kHz),
#    and Cal_3C444_Ch169 (1449573440) for the 1449551392 drift images. Parameters go in
#    through the environment: sbatch --export splits at commas (21 Oct).
# 2. asvo-watch.sbatch (downloads every Ready job not yet on the NAS).
# 3. composite product 1449551392_ch161-158_drift_h (ch 161 then ch 158 along the harmonic lane).
# 4. run_products.sh for products/drift_1449551392.txt (PAR=2) and products/batch2.txt (PAR=2).
set -uo pipefail
E=$HOME/mwa/events
PARAMS_CAL="output=ms,avg_time_res=2,avg_freq_res=160,flag_edge_width=80,no_rfi=true"
cd "$HOME/mwa"

# 1. ASVO requests (skip obsids the ledger already covers: see configs/asvo_jobs.csv)
SUBMIT=vis OBSIDS="1339475176 1347335176 1347594008 1387165944 1406167216" \
  sbatch -M calc-cpu --export=ALL "$E/asvo-submit-retry.sbatch"
SUBMIT=vis OBSIDS="1407292216 1416884416 1419137056 1419477136" \
  sbatch -M calc-cpu --export=ALL "$E/asvo-submit-retry.sbatch"
SUBMIT=conv PARAMS=$PARAMS_CAL OBSIDS="1339452016 1347359296 1347571816 1348574416 1387139416" \
  sbatch -M calc-cpu --export=ALL "$E/asvo-submit-retry.sbatch"
SUBMIT=conv PARAMS=$PARAMS_CAL OBSIDS="1406154616 1407276200 1416862472 1419455048 1449573440" \
  sbatch -M calc-cpu --export=ALL "$E/asvo-submit-retry.sbatch"

# 2. download watcher (after the submissions have had time to register)
sbatch -M calc-cpu --begin=now+10minutes "$HOME/mwa/asvo-watch.sbatch"

# 3. composite drift product (frames of the two harmonic-lane runs in time order)
mkdir -p "$HOME/mwa/products"
python3 - <<'EOF'
import json, os
f = os.path.expanduser("~/mwa/products/1449551392_ch161-158_drift_h.json")
json.dump(dict(product="1449551392_ch161-158_drift_h", sun="1449551392", ch="161>158", cal="1449573440",
               cal_job="", datedir="20251212", label="drift_h", tres="2",
               trange="2025/12/12/05:09:34~2025/12/12/05:11:34",
               parts=["1449551392_ch161_drift_h_ch161", "1449551392_ch158_drift_h_ch158"],
               note="2 s images along the harmonic lane (e-Callisto drift -0.039 MHz/s): ch 161 to 05:10:16, then ch 158",
               attempts=[]), open(f, "w"), indent=1)
print("composite product registered")
EOF

# 4. product lists, detached
mkdir -p "$HOME/mwa/products/logs"
PAR=2 setsid nohup bash "$E/run_products.sh" "$E/drift_1449551392.txt" > "$HOME/mwa/products/logs/drift_1449551392.out" 2>&1 < /dev/null &
PAR=2 setsid nohup bash "$E/run_products.sh" "$E/batch2.txt" > "$HOME/mwa/products/logs/batch2.out" 2>&1 < /dev/null &
echo "round started; status: ~/mwa/products/logs/{drift_1449551392,batch2}.status, ~/mwa/asvo-watch.status"
