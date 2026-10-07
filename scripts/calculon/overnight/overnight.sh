#!/bin/bash
# Unattended run on calculon for the 2022-09-30 bursts (started 2026-10-08).
# Runs detached on the login node, mostly sleeping; all work is in Slurm jobs.
#   setsid nohup bash ~/overnight/bin/overnight.sh > ~/overnight/driver.log 2>&1 < /dev/null &
# Progress: ~/overnight/PROGRESS.md, plus a mail per step via a 1-second Slurm job whose
# name is the message (Slurm --mail-type=END). Results: ~/overnight/REPORT.md.
set -uo pipefail

MAIL=andre.csillaghy@fhnw.ch
BIN=$HOME/overnight/bin
R=$HOME/overnight                       # small text outputs (NFS home)
S=/scratch/$USER/overnight              # images, logs
P=/scratch/$USER/paircars
F=/scratch/$USER/mwa/flare20220930
SUN=1348547272
CAL=1348574416
TRANGE="2022/09/30/04:28:30~2022/09/30/04:29:02,2022/09/30/04:31:24~2022/09/30/04:31:40"
mkdir -p "$R" "$S/img" "$S/logs" "$S/analysis"
PROG=$R/PROGRESS.md

log() { echo "- $(date '+%Y-%m-%d %H:%M') $*" | tee -a "$PROG"; }
notify() {  # mail via Slurm: the job name is the message
  local msg="OVERNIGHT: $*"
  sbatch -M calc-cpu -p cpu-daily --time=00:01:00 -n1 -c1 --mem=50M -J "${msg:0:120}" \
    -o /dev/null --mail-type=END --mail-user="$MAIL" --wrap true >/dev/null 2>&1 || true
  log "$*"
}
jobid() { awk '{print $4}'; }           # "Submitted batch job N [on cluster X]"
wait_jobs() {  # wait until none of the given "cluster:jobid" are queued/running
  while :; do
    local busy=0
    for cj in "$@"; do
      local c=${cj%%:*} j=${cj##*:}
      squeue -M "$c" -h -j "$j" 2>/dev/null | grep -q . && busy=1
    done
    [[ $busy == 0 ]] && return
    sleep 300
  done
}
state() { sacct -M "${1%%:*}" -j "${1##*:}" -X -n -o State 2>/dev/null | head -1 | tr -d ' '; }

echo "# Overnight run $(date '+%Y-%m-%d %H:%M')" > "$PROG"
notify "started (extract, wide-field images, then P-AIRCARS 24 ch)"

# --- A: extraction (CPU) and wide-field images (GPU) in parallel -------------
cd "$S/logs"
e1=$(sbatch -M calc-cpu -o "$S/logs/%x_%j.log" --mail-type=FAIL --mail-user=$MAIL \
     --export=ALL,OBSID=$SUN "$BIN/extract-all.sbatch" | jobid)
e2=$(sbatch -M calc-cpu -o "$S/logs/%x_%j.log" --mail-type=FAIL --mail-user=$MAIL \
     --export=ALL,OBSID=$CAL "$BIN/extract-all.sbatch" | jobid)
pms=$(ls -d $P/out/$SUN/20220930/${SUN}_target/calibrated_ms/*.ms | head -1)
w1=$(sbatch -o "$S/logs/%x_%j.log" --mail-type=FAIL --mail-user=$MAIL -J wide-3C444 \
     --export=ALL,MS=$F/${CAL}_ch112.ms,SOLUTIONS=$F/cal/hyp_soln_${CAL}_ch112.fits,METAFITS=$F/${CAL}.metafits,NAME=3C444_ch112_wide,OUTDIR=$S/img \
     "$BIN/wide-field.sbatch" | jobid)
w2=$(sbatch -o "$S/logs/%x_%j.log" --mail-type=FAIL --mail-user=$MAIL -J wide-sun-hyp \
     --export=ALL,MS=$F/${SUN}_ch112_noaof_cal.ms,NAME=sun_ch112_hyperdrive_wide,MULTISCALE=1,MINUV=150,OUTDIR=$S/img \
     "$BIN/wide-field.sbatch" | jobid)
w3=$(sbatch -o "$S/logs/%x_%j.log" --mail-type=FAIL --mail-user=$MAIL -J wide-sun-pai \
     --export=ALL,MS=$pms,DATACOL=CORRECTED_DATA,NAME=sun_ch112_paircars_wide,MULTISCALE=1,MINUV=150,OUTDIR=$S/img \
     "$BIN/wide-field.sbatch" | jobid)
log "submitted extract $e1 $e2 (calc-cpu), wide-field $w1 $w2 $w3 (GPU cluster)"

# --- B: P-AIRCARS on all 24 channels once both obs are extracted -------------
wait_jobs "calc-cpu:$e1" "calc-cpu:$e2"
n1=$(ls -d $P/data/${SUN}_all/*.ms 2>/dev/null | wc -l); n2=$(ls -d $P/data/${CAL}_all/*.ms 2>/dev/null | wc -l)
if [[ $n1 -lt 24 || $n2 -lt 24 ]]; then
  notify "extraction incomplete ($n1/$n2 MS) - P-AIRCARS not started"
  pai_ok=0
else
  log "extracted $n1 + $n2 MS"
  source ~/paircars/env.sh >/dev/null 2>&1
  run-mwa-paircars $P/data/${SUN}_all --target_metafits $P/data/${SUN}_all/${SUN}.metafits \
    --cal_datadir $P/data/${CAL}_all --cal_metafits $P/data/${CAL}_all/${CAL}.metafits \
    --workdir $P/work/${SUN}_all --outdir $P/out/${SUN}_all \
    --do_forcereset_weightflag --timerange "$TRANGE" --image_timeres 4 --pol I --no_polcal \
    --cpu_frac 0.05 --mem_frac 0.05 --cluster --partition cpu-daily --max_worker 4 --walltime 12:00:00 \
    > "$S/logs/paircars-submit.out" 2>&1
  pid=$(grep -oE "Job ID: [0-9]+" "$S/logs/paircars-submit.out" | head -1 | awk '{print $3}')
  if [[ -z $pid ]]; then
    notify "P-AIRCARS submission failed (see $S/logs/paircars-submit.out)"; pai_ok=0
  else
    notify "P-AIRCARS 24-channel run $pid submitted"
    mlog=$P/work/${SUN}_all/main_paircars_$pid.log
    pai_ok=2
  fi
fi

# --- C: position check once the wide-field images are done -------------------
wait_jobs "cluster:$w1" "cluster:$w2" "cluster:$w3"
log "wide-field jobs: $(state cluster:$w1) $(state cluster:$w2) $(state cluster:$w3)"
cat > "$S/analysis/gleam.sh" <<EOF
source \$HOME/mwa/mwa-env.sh
run() { singularity exec --bind /scratch "\$MWA_DEMO_SIF" "\$@"; }
cd $S/analysis
[ -f $S/img/3C444_ch112_wide-image.fits ] && run python3 $BIN/gleam_check.py $S/img/3C444_ch112_wide-image.fits \$HOME/mwa/cal/GGSM_updated.fits gleam_3C444 --min-flux 5
for n in sun_ch112_hyperdrive_wide sun_ch112_paircars_wide; do
  [ -f $S/img/\$n-image.fits ] && run python3 $BIN/gleam_check.py $S/img/\$n-image.fits \$HOME/mwa/cal/GGSM_updated.fits gleam_\$n --sun --min-flux 5
done
echo GLEAM_DONE
EOF
g=$(sbatch -M calc-cpu -p cpu-daily --time=01:00:00 -n1 -c2 --mem=8G -J gleam-check -o "$S/logs/%x_%j.log" \
    --mail-type=FAIL --mail-user=$MAIL "$S/analysis/gleam.sh" | jobid)
wait_jobs "calc-cpu:$g"
notify "position check done ($(state calc-cpu:$g)): see ~/overnight/REPORT.md"

# --- D: flux check once P-AIRCARS has finished --------------------------------
if [[ $pai_ok == 2 ]]; then
  until grep -q "P-AIRCARS execution is finished" "$mlog" 2>/dev/null; do
    squeue -M calc-cpu -h -n "paircars_$pid" | grep -q . || { sleep 120; grep -q "execution is finished" "$mlog" 2>/dev/null || break; }
    sleep 300
  done
  res=$(grep -oE "execution is finished: [A-Za-z]+" "$mlog" | tail -1)
  notify "P-AIRCARS 24-channel run $pid: ${res:-ended without a result line}"
  hpc=$(ls -d $P/out/${SUN}_all/20220930/${SUN}_target/imagedir_*/pbcor_hpcs 2>/dev/null | head -1)
  if [[ -n $hpc ]]; then
    q=$(sbatch -M calc-cpu -p cpu-daily --time=01:00:00 -n1 -c2 --mem=16G -J flux-check -o "$S/logs/%x_%j.log" \
        --mail-type=FAIL --mail-user=$MAIL --wrap "source \$HOME/mwa/mwa-env.sh; cd $S/analysis; \
        singularity exec --bind /scratch \$MWA_DEMO_SIF python3 $BIN/quiet_sun_flux.py $hpc quiet_sun --t0 20220930043124 --t1 20220930043140; \
        singularity exec --bind /scratch \$MWA_DEMO_SIF python3 $BIN/quiet_sun_flux.py $hpc burst --t0 20220930042828 --t1 20220930042900" | jobid)
    wait_jobs "calc-cpu:$q"
    log "flux check: $(state calc-cpu:$q)"
  else
    log "no P-AIRCARS images found for the flux check"
  fi
fi

# --- E: report ------------------------------------------------------------------
{
  echo "# Overnight report $(date '+%Y-%m-%d %H:%M')"
  echo; echo "## Progress"; cat "$PROG"
  echo; echo "## Position check (GGSM)"
  for f in "$S"/analysis/gleam_*.json; do
    [ -f "$f" ] && { echo "### $(basename "$f")"; echo '```'; python3 -c "import json,sys; print(json.dumps(json.load(open(sys.argv[1]))['summary'], indent=1))" "$f"; echo '```'; }
  done
  echo; echo "## Flux check (P-AIRCARS, 24 channels)"
  for f in "$S"/analysis/quiet_sun.json "$S"/analysis/burst.json; do
    [ -f "$f" ] && { echo "### $(basename "$f")"; echo '```'; cat "$f"; echo '```'; }
  done
  echo; echo "Plots: $S/analysis/*.png; images: $S/img; P-AIRCARS: $P/out/${SUN}_all"
} > "$R/REPORT.md"
notify "all done - report in ~/overnight/REPORT.md"
