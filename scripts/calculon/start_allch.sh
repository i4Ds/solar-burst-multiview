#!/bin/bash
# All archived channels of 1449551392 in 2 s over the whole obs (23 Oct 2026).
#   bash ~/mwa/events/start_allch.sh          (login node; returns at once)
# 1. ASVO conversions of Cal_3C444_Ch93 (1449573272) and Cal_3C444_Ch145 (1449573384):
#    no_rfi=true, 2 s, 160 kHz, edge 80 (native 10 kHz); parameters through the environment.
# 2. one Slurm job extracts the metafits and the gpubox files of 9 channels (ch 132 has its MS) from the tar,
#    so the product runs skip their own tar scan.
# 3. drift composite re-registered on the full-obs runs of ch 161 (to 05:10:16) and ch 158 (after).
# 4. run_products.sh allch_1449551392.txt with PAR=3, after the extraction job.
set -uo pipefail
E=$HOME/mwa/events
SUN=1449551392
W=/scratch/$USER/mwa/events/$SUN
TAR=/mnt/nas05/data02/MWA_data/data/mwa_data2/${SUN}_1114412_vis.tar
CHS="097 138 143 146 152 158 161 167 173"
cd "$HOME/mwa"

SUBMIT=conv PARAMS="output=ms,avg_time_res=2,avg_freq_res=160,flag_edge_width=80,no_rfi=true" \
  OBSIDS="1449573272 1449573384" sbatch -M calc-cpu --export=ALL "$E/asvo-submit-retry.sbatch"

mkdir -p "$W" "$HOME/mwa/products/logs"
pat=$(for c in $CHS; do printf ' "*_ch%s_*.fits"' "$c"; done)
jx=$(sbatch -M calc-cpu --parsable -p cpu-daily --time=04:00:00 -n1 -c2 --mem=4G -J extract-$SUN \
  -o "$HOME/mwa/products/logs/extract_${SUN}_allch_%j.log" \
  --wrap "set -e; cd $W; tar -xvf $TAR --wildcards '*${SUN}.metafits' $pat; \
    find $W -mindepth 2 \\( -name '*.fits' -o -name '*.metafits' \\) -exec mv {} $W/ \; ; ls $W | wc -l; echo EXTRACT_ALLCH_OK" | cut -d';' -f1)
echo "extraction job $jx"

python3 - <<'PY'
import json, os
f = os.path.expanduser("~/mwa/products/1449551392_ch161-158_drift_h.json")
json.dump(dict(product="1449551392_ch161-158_drift_h", sun="1449551392", ch="161>158", cal="1449573440",
               cal_job="", datedir="20251212", label="drift_h", tres="2",
               trange="2025/12/12/05:09:34~2025/12/12/05:11:34",
               parts=[dict(product="1449551392_ch161_s2_full", to="2025-12-12T05:10:16"),
                      dict(product="1449551392_ch158_s2_full", **{"from": "2025-12-12T05:10:16"})],
               note="2 s images along the harmonic lane (e-Callisto drift -0.039 MHz/s): ch 161 to 05:10:16, then ch 158",
               attempts=[]), open(f, "w"), indent=1)
print("composite product re-registered")
PY

# product runs once the extraction is done (waits detached on the login node)
setsid nohup bash -c "while squeue -M calc-cpu -h -j $jx 2>/dev/null | grep -q .; do sleep 60; done; \
  grep -q EXTRACT_ALLCH_OK $HOME/mwa/products/logs/extract_${SUN}_allch_$jx.log || { echo extraction failed; exit 1; }; \
  PAR=3 bash $E/run_products.sh $E/allch_1449551392.txt" \
  > "$HOME/mwa/products/logs/allch_1449551392.out" 2>&1 < /dev/null &
echo "started; status: ~/mwa/products/logs/allch_1449551392.status"
