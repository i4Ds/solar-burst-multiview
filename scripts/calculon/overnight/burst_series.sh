#!/bin/bash
# P-AIRCARS image series of one coarse channel from a given MS (e.g. the 2 s
# re-conversion), with its own workdir/outdir so calibration and self-cal are
# redone for that data. Runs detached on the login node:
#   setsid nohup bash ~/overnight/bin/burst_series.sh > ~/overnight/<TAG>.log 2>&1 < /dev/null &
# Environment (defaults: the 2 s ch116 series of the 04:28 burst):
#   SRC_MS    MS to image (copied into the P-AIRCARS data dir)
#   METAFITS  metafits of that obs
#   TAG       name for data/work/out dirs and outputs
#   TRANGE    P-AIRCARS --timerange;  TRES  --image_timeres (s)
# Status: ~/overnight/<TAG>.md; PNG: /scratch/$USER/overnight/analysis/<TAG>.png
set -uo pipefail
SUN=1348547272; CAL=1348574416
SRC_MS=${SRC_MS:-/scratch/$USER/mwa/flare20220930_025s/1348547272_ch116.ms}
METAFITS=${METAFITS:-/scratch/$USER/mwa/flare20220930_025s/1348547272.metafits}
TAG=${TAG:-1348547272_2s_ch116}
TRANGE=${TRANGE:-2022/09/30/04:28:20~2022/09/30/04:29:10}
TRES=${TRES:-2}
MAIL=andre.csillaghy@fhnw.ch
BIN=$HOME/overnight/bin
P=/scratch/$USER/paircars
S=/scratch/$USER/overnight
ST=$HOME/overnight/$TAG.md
log() { echo "- $(date '+%Y-%m-%d %H:%M') $*" | tee -a "$ST"; }
notify() { sbatch -M calc-cpu -p cpu-daily --time=00:01:00 -n1 -c1 --mem=50M -J "$TAG: ${*:0:100}" \
  -o /dev/null --mail-type=END --mail-user=$MAIL --wrap true >/dev/null 2>&1 || true; log "$*"; }
waitjob() { while squeue -M calc-cpu -h -j "$1" 2>/dev/null | grep -q .; do sleep 60; done; }

mkdir -p "$S/logs" "$S/analysis"
echo "# $TAG, started $(date '+%Y-%m-%d %H:%M') (src $SRC_MS, $TRANGE, ${TRES} s)" > "$ST"
D=$P/data/$TAG
if [[ ! -d $D/$(basename "$SRC_MS") ]]; then
  j=$(sbatch -M calc-cpu -p cpu-daily --time=00:30:00 -n1 -c1 --mem=2G -J copy-$TAG -o "$S/logs/%x_%j.log" \
      --wrap "mkdir -p $D && cp -a $SRC_MS $METAFITS $D/ && echo COPY_OK" | awk '{print $4}')
  waitjob "$j"
fi
[[ -d $D/$(basename "$SRC_MS") ]] || { notify "copy failed"; exit 1; }
log "data ready in $D"

source ~/paircars/env.sh >/dev/null 2>&1
run-mwa-paircars $D --target_metafits $D/$(basename "$METAFITS") \
  --cal_datadir $P/data/${CAL}_all --cal_metafits $P/data/${CAL}_all/${CAL}.metafits \
  --workdir $P/work/$TAG --outdir $P/out/$TAG \
  --do_forcereset_weightflag --timerange "$TRANGE" --image_timeres "$TRES" --pol I --no_polcal \
  --cpu_frac 0.05 --mem_frac 0.05 --cluster --partition cpu-daily --max_worker 1 --walltime 06:00:00 \
  > "$S/logs/$TAG-submit.out" 2>&1
pid=$(grep -oE "Job ID: [0-9]+" "$S/logs/$TAG-submit.out" | head -1 | awk '{print $3}')
[[ -n $pid ]] || { notify "P-AIRCARS submission failed"; exit 1; }
log "P-AIRCARS job $pid submitted"
mlog=$P/work/$TAG/main_paircars_$pid.log
until grep -q "P-AIRCARS execution is finished" "$mlog" 2>/dev/null; do
  squeue -M calc-cpu -h -n "paircars_$pid" | grep -q . || { sleep 120; grep -q "execution is finished" "$mlog" 2>/dev/null || break; }
  sleep 120
done
res=$(grep -oE "execution is finished: [A-Za-z]+" "$mlog" | tail -1)
log "P-AIRCARS: ${res:-ended without a result line}"
img=$(ls -d $P/out/$TAG/20220930/${SUN}_target/imagedir_* 2>/dev/null | head -1)
n=$(ls "$img"/pbcor_hpcs/*.fits 2>/dev/null | wc -l)
log "$n images in $img/pbcor_hpcs"
if [[ $n -gt 0 ]]; then
  j=$(sbatch -M calc-cpu -p cpu-daily --time=00:30:00 -n1 -c2 --mem=8G -J plot-$TAG -o "$S/logs/%x_%j.log" \
      --wrap "source \$HOME/mwa/mwa-env.sh; R(){ singularity exec --bind /scratch \$MWA_DEMO_SIF \"\$@\"; }; \
      R python3 $BIN/make_cube.py $img/pbcor_hpcs $S/analysis/$TAG.npz && \
      R python3 $BIN/montage.py $S/analysis/$TAG.npz $S/analysis/$TAG.png" | awk '{print $4}')
  waitjob "$j"
fi
if [[ -f $S/analysis/$TAG.png ]]; then notify "done: $n images, PNG in $S/analysis/$TAG.png"
else notify "finished with problems (${res:-no result}); see ~/overnight/$TAG.md"; fi
