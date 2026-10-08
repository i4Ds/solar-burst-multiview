#!/bin/bash
# Ten 4 s P-AIRCARS images of the 04:28 burst (2022-09-30, obs 1348547272) in one
# coarse channel, reusing the 3C444 and self-cal tables of the 24-channel run.
# Runs detached on the login node:
#   setsid nohup bash ~/overnight/bin/burst10.sh 116 > ~/overnight/burst10.log 2>&1 < /dev/null &
# Status: ~/overnight/BURST10.md; result PNG: /scratch/$USER/overnight/analysis/burst10_ch<CH>.png
set -uo pipefail
CH=${1:-116}
MAIL=andre.csillaghy@fhnw.ch
BIN=$HOME/overnight/bin
P=/scratch/$USER/paircars
S=/scratch/$USER/overnight
SUN=1348547272; CAL=1348574416
TRANGE="2022/09/30/04:28:26~2022/09/30/04:29:06"
ST=$HOME/overnight/BURST10.md
log() { echo "- $(date '+%Y-%m-%d %H:%M') $*" | tee -a "$ST"; }
notify() { sbatch -M calc-cpu -p cpu-daily --time=00:01:00 -n1 -c1 --mem=50M -J "BURST10: ${*:0:100}" \
  -o /dev/null --mail-type=END --mail-user=$MAIL --wrap true >/dev/null 2>&1 || true; log "$*"; }
waitjob() { while squeue -M calc-cpu -h -j "$1" 2>/dev/null | grep -q .; do sleep 60; done; }

echo "# Burst series ch$CH, started $(date '+%Y-%m-%d %H:%M')" > "$ST"
D=$P/data/${SUN}_ch$CH
if [[ ! -d $D/${SUN}_ch$CH.ms ]]; then
  j=$(sbatch -M calc-cpu -p cpu-daily --time=00:30:00 -n1 -c1 --mem=2G -J copy-ch$CH -o "$S/logs/%x_%j.log" \
      --wrap "mkdir -p $D && cp -a $P/data/${SUN}_all/${SUN}_ch$CH.ms $P/data/${SUN}_all/${SUN}.metafits $D/ && echo COPY_OK" | awk '{print $4}')
  waitjob "$j"
fi
[[ -d $D/${SUN}_ch$CH.ms ]] || { notify "copy of ch$CH failed"; exit 1; }
log "data ready in $D"

T=$P/out/${SUN}_all/20220930/${SUN}_target
img=$T/imagedir_f_1.28_t_4.0_pol_I_w_briggs_0.0
[[ -d $img ]] && mv "$img" "${img}_moved_$(date +%Y%m%d%H%M)"
source ~/paircars/env.sh >/dev/null 2>&1
run-mwa-paircars $D --target_metafits $D/${SUN}.metafits \
  --cal_datadir $P/data/${CAL}_all --cal_metafits $P/data/${CAL}_all/${CAL}.metafits \
  --workdir $P/work/${SUN}_all --outdir $P/out/${SUN}_all \
  --do_forcereset_weightflag --timerange "$TRANGE" --image_timeres 4 --pol I --no_polcal \
  --cpu_frac 0.05 --mem_frac 0.05 --cluster --partition cpu-daily --max_worker 1 --walltime 06:00:00 \
  > "$S/logs/burst10-submit.out" 2>&1
pid=$(grep -oE "Job ID: [0-9]+" "$S/logs/burst10-submit.out" | head -1 | awk '{print $3}')
[[ -n $pid ]] || { notify "P-AIRCARS submission failed"; exit 1; }
log "P-AIRCARS job $pid submitted"
mlog=$P/work/${SUN}_all/main_paircars_$pid.log
until grep -q "P-AIRCARS execution is finished" "$mlog" 2>/dev/null; do
  squeue -M calc-cpu -h -n "paircars_$pid" | grep -q . || { sleep 120; grep -q "execution is finished" "$mlog" 2>/dev/null || break; }
  sleep 120
done
res=$(grep -oE "execution is finished: [A-Za-z]+" "$mlog" | tail -1)
log "P-AIRCARS: ${res:-ended without a result line}"
mv "$img" "${img}_burst10_ch$CH" 2>/dev/null && img=${img}_burst10_ch$CH
n=$(ls "$img"/pbcor_hpcs/*.fits 2>/dev/null | wc -l)
log "$n images in $img/pbcor_hpcs"
if [[ $n -gt 0 ]]; then
  j=$(sbatch -M calc-cpu -p cpu-daily --time=00:30:00 -n1 -c2 --mem=8G -J burst10-plot -o "$S/logs/%x_%j.log" \
      --wrap "source \$HOME/mwa/mwa-env.sh; R(){ singularity exec --bind /scratch \$MWA_DEMO_SIF \"\$@\"; }; \
      R python3 $BIN/make_cube.py $img/pbcor_hpcs $S/analysis/burst10_ch$CH.npz && \
      R python3 $BIN/montage.py $S/analysis/burst10_ch$CH.npz $S/analysis/burst10_ch$CH.png" | awk '{print $4}')
  waitjob "$j"
fi
if [[ -f $S/analysis/burst10_ch$CH.png ]]; then
  notify "done: $n images, PNG in $S/analysis/burst10_ch$CH.png"
else
  notify "finished with problems (${res:-no result}); see ~/overnight/BURST10.md"
fi
