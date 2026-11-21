#!/bin/bash
# Unattended: wait for the Figure 4 ASVO tars, extract the four bands, run
# P-AIRCARS (Cen A solutions applied to the Sun). Login node, detached:
#   setsid nohup bash ~/overnight/bin/fig4_raw_chain.sh \
#     > ~/overnight/fig4_raw_chain.log 2>&1 < /dev/null &
# Status: ~/overnight/fig4_raw_chain.md and mail at each stage.
# Downloads already submitted (216541 Sun, 216542 Cen A). This script waits
# for them. It does not touch Rohit's tree.
#
# First imaging is one map per coarse channel over the scan, plus the
# calibrated measurement sets. Half-second frames (570 per band) are a
# second run once those solutions exist.
set -uo pipefail
MAIL=andre.csillaghy@fhnw.ch
DL=/mnt/nas05/data02/MWA_data/data/mwa_data2
W=/scratch/$USER/mwa/sharma2020/raw
P=/scratch/$USER/paircars
SUN=1133149192; SUNJOB=1124199; SUNBYTES=54632642560; SUNDL=216541
CAL=1133139776; CALJOB=1124200; CALBYTES=2540001280; CALDL=216542
CHANS="084 085 125 126 169 170 187 188"
# Must sit inside the unflagged data (03:39:41–03:44:25). A range that
# starts at 03:39:37 produced an empty image directory.
TRANGE="2015/12/03/03:39:44~2015/12/03/03:44:24"
TRES=280
WALL=23:00:00
ST=$HOME/overnight/fig4_raw_chain.md
log() { echo "- $(date '+%Y-%m-%d %H:%M') $*" | tee -a "$ST"; }
notify() {
  sbatch -M calc-cpu -p cpu-daily --time=00:01:00 -n1 -c1 --mem=50M \
    -J "fig4raw: ${*:0:90}" -o /dev/null --mail-type=END --mail-user=$MAIL \
    --wrap true >/dev/null 2>&1 || true
  log "$*"
}
waitjob() { while squeue -M calc-cpu -h -j "$1" 2>/dev/null | grep -q .; do sleep 60; done; }
jid() { awk '{print $4}'; }

mkdir -p "$HOME/overnight" "$HOME/mwa/logs" "$W"
echo "# fig4 raw chain, started $(date '+%Y-%m-%d %H:%M')" >> "$ST"
cd "$HOME/mwa" || exit 1

# 1. Wait for the downloads already running (do not submit new ones).
log "waiting for downloads $SUNDL (Sun) and $CALDL (Cen A)"
waitjob "$SUNDL"
waitjob "$CALDL"
for spec in "$SUN:$SUNBYTES:$SUNJOB" "$CAL:$CALBYTES:$CALJOB"; do
  o=${spec%%:*}; rest=${spec#*:}; bytes=${rest%%:*}; job=${rest##*:}
  tar="$DL/${o}_${job}_ms.tar"
  sz=$(stat -c %s "$tar" 2>/dev/null || echo 0)
  if [[ $sz -lt $bytes ]]; then
    notify "download of $o incomplete ($sz < $bytes bytes)"
    exit 1
  fi
done
notify "downloads complete"

# 2. Extract the eight Figure 4 coarse channels and the metafits.
j=$(sbatch -M calc-cpu -p cpu-daily --time=03:00:00 -n1 -c1 --mem=4G \
  -J extract-fig4 -o logs/extract-fig4_%j.log --wrap \
  "set -e; bash \$HOME/mwa/extract-fig4.sh $SUN $SUNJOB; bash \$HOME/mwa/extract-fig4.sh $CAL $CALJOB; echo EXTRACT_ALL_OK" | jid)
log "extract job $j"
waitjob "$j"
grep -q EXTRACT_ALL_OK logs/extract-fig4_${j}.log || {
  notify "extraction failed, see ~/mwa/logs/extract-fig4_${j}.log"
  exit 1
}
notify "extraction done (108, 162, 217, 240 MHz)"

# 3. Prefect must be up on the login node before P-AIRCARS workers start.
if ! curl -s --max-time 8 http://calc-m-001:4260/api/health | grep -q true; then
  log "starting Prefect"
  source "$HOME/paircars/env.sh"
  mkdir -p /scratch/$USER/paircars/logs
  setsid nohup python -u -c \
    'from paircars.utils.prefect_setup_utils import start_prefect_server; start_prefect_server(4260, 5260, scheduler_name="slurm")' \
    > /scratch/$USER/paircars/logs/prefect-start-fig4.out 2>&1 < /dev/null &
  for i in $(seq 30); do
    curl -s --max-time 5 http://calc-m-001:4260/api/health 2>/dev/null | grep -q true && break
    sleep 20
  done
fi
curl -s --max-time 8 http://calc-m-001:4260/api/health | grep -q true || {
  notify "Prefect did not start; see /scratch/$USER/paircars/logs/prefect-start-fig4.out"
  exit 1
}
log "Prefect is up"

# 4. P-AIRCARS data directories (Sun and Cen A, four bands only).
SUND=$P/data/${SUN}_fig4
CALD=$P/data/${CAL}_fig4
j=$(sbatch -M calc-cpu -p cpu-daily --time=01:00:00 -n1 -c1 --mem=2G \
  -J copy-fig4-pcars -o logs/copy-fig4-pcars_%j.log --wrap "
set -e
mkdir -p $SUND $CALD
cp -a $W/$SUN/*.ms $W/$SUN/$SUN.metafits $SUND/
cp -a $W/$CAL/*.ms $W/$CAL/$CAL.metafits $CALD/
ls $SUND $CALD
echo COPY_OK
" | jid)
waitjob "$j"
grep -q COPY_OK logs/copy-fig4-pcars_${j}.log || {
  notify "copy into P-AIRCARS data dirs failed"
  exit 1
}

notify "starting P-AIRCARS (Cen A, then the Sun; one map per channel over the scan)"
source "$HOME/paircars/env.sh"
TAG=fig4_raw
SUB=$HOME/overnight/fig4_raw_submit.out
run-mwa-paircars "$SUND" \
  --target_metafits "$SUND/${SUN}.metafits" \
  --cal_datadir "$CALD" --cal_metafits "$CALD/${CAL}.metafits" \
  --workdir "$P/work/$TAG" --outdir "$P/out/$TAG" \
  --do_forcereset_weightflag --keep_calibrated_ms --no_selfcal --no_apply_selfcal \
  --timerange "$TRANGE" --image_timeres "$TRES" --pol I --no_polcal \
  --cpu_frac 0.05 --mem_frac 0.05 \
  --cluster --partition cpu-daily --max_worker 4 --walltime "$WALL" \
  > "$SUB" 2>&1
pid=$(grep -oE "Job ID: [0-9]+" "$SUB" | head -1 | awk '{print $3}')
[[ -n $pid ]] || { notify "P-AIRCARS submission failed; see ~/overnight/fig4_raw_submit.out"; exit 1; }
log "P-AIRCARS job $pid submitted"
mlog=$P/work/$TAG/main_paircars_$pid.log
until grep -q "P-AIRCARS execution is finished" "$mlog" 2>/dev/null; do
  squeue -M calc-cpu -h -n "paircars_$pid" | grep -q . || {
    sleep 120
    grep -q "execution is finished" "$mlog" 2>/dev/null || break
  }
  sleep 120
done
res=$(grep -oE "execution is finished: [A-Za-z]+" "$mlog" | tail -1)
notify "P-AIRCARS: ${res:-ended without a result line}; log $mlog"
ls -d "$P/out/$TAG"/* 2>/dev/null | head
echo DONE >> "$ST"
