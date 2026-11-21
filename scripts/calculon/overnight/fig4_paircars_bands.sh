#!/bin/bash
# P-AIRCARS of the four Figure 4 bands, same recipe as 145.9 MHz (ch113-114,
# 14–15 October 2026): 4 s ASVO, 3C444, one map over the scan, then a second
# run without self-cal.
#
#   setsid nohup bash ~/overnight/bin/fig4_paircars_bands.sh \
#     > ~/overnight/fig4_paircars_bands.log 2>&1 < /dev/null &
#
# Status: ~/overnight/fig4_paircars_bands.md
# Cubes: /scratch/$USER/overnight/analysis/1133149192_ch<pair>_{quiet,noself}.npz
# Does not touch Rohit's tree. Does not process the 40 kHz Figure 4 conversion.
set -uo pipefail
MAIL=andre.csillaghy@fhnw.ch
BIN=$HOME/overnight/bin
DL=/mnt/nas05/data02/MWA_data/data/mwa_data2
W=/scratch/$USER/mwa/quiet2015
P=/scratch/$USER/paircars
SUN=1133149192; SUNJOB=1113526
CAL=1133161488; CALJOB=1113527
TRANGE="2015/12/03/03:39:44~2015/12/03/03:44:24"
TRES=280
PAIRS=(84-85 125-126 169-170 187-188)
ST=$HOME/overnight/fig4_paircars_bands.md
log() { echo "- $(date '+%Y-%m-%d %H:%M') $*" | tee -a "$ST"; }
notify() {
  sbatch -M calc-cpu -p cpu-daily --time=00:01:00 -n1 -c1 --mem=50M \
    -J "fig4pc: ${*:0:90}" -o /dev/null --mail-type=END --mail-user=$MAIL \
    --wrap true >/dev/null 2>&1 || true
  log "$*"
}
waitjob() { while squeue -M calc-cpu -h -j "$1" 2>/dev/null | grep -q .; do sleep 60; done; }
jid() { awk '{print $4}'; }

mkdir -p "$HOME/overnight" "$HOME/mwa/logs" "$W/$SUN" "$W/$CAL"
echo "# fig4 P-AIRCARS bands, started $(date '+%Y-%m-%d %H:%M')" >> "$ST"
cd "$HOME/mwa" || exit 1

# 1. Extract the four Figure 4 pairs from the October 4 s tars (already on NAS).
j=$(sbatch -M calc-cpu -p cpu-daily --time=02:00:00 -n1 -c1 --mem=4G \
  -J extract-fig4pc -o logs/extract-fig4pc_%j.log \
  --wrap "bash $BIN/extract-fig4-4s.sh" | jid)
log "extract job $j"
waitjob "$j"
grep -q EXTRACT_OK logs/extract-fig4pc_${j}.log || {
  notify "extraction failed, see ~/mwa/logs/extract-fig4pc_${j}.log"
  exit 1
}
notify "extraction done (84-85, 125-126, 169-170, 187-188)"

# 2. One P-AIRCARS run per pair: self-cal (LABEL=quiet), then no self-cal.
#    Same flags as 14–15 October ch113-114.
for pair in "${PAIRS[@]}"; do
  SUNMS=$W/$SUN/${SUN}_ch${pair}.ms
  CALMS=$W/$CAL/${CAL}_ch${pair}.ms
  if [[ ! -d $SUNMS || ! -d $CALMS ]]; then
    notify "missing MS for ch${pair}"
    continue
  fi
  CALDIR=$P/data/${CAL}_ch${pair}
  mkdir -p "$CALDIR"
  if [[ ! -d $CALDIR/$(basename "$CALMS") ]]; then
    cp -a "$CALMS" "$W/$CAL/${CAL}.metafits" "$CALDIR/"
  fi

  notify "starting P-AIRCARS self-cal ch${pair}"
  SUN=$SUN CAL=$CAL CALDIR=$CALDIR DATEDIR=20151203 \
    SRC_MS=$SUNMS METAFITS=$W/$SUN/${SUN}.metafits \
    TAG=${SUN}_ch${pair} TRANGE="$TRANGE" TRES=$TRES LABEL=quiet \
    bash "$BIN/burst_series.sh"

  notify "starting P-AIRCARS no-self-cal ch${pair}"
  SUN=$SUN CAL=$CAL CALDIR=$CALDIR DATEDIR=20151203 \
    SRC_MS=$SUNMS METAFITS=$W/$SUN/${SUN}.metafits \
    TAG=${SUN}_ch${pair}_noself TRANGE="$TRANGE" TRES=$TRES LABEL=noself \
    EXTRA="--no_selfcal --keep_calibrated_ms" \
    bash "$BIN/burst_series.sh"
done

notify "all four pairs finished; cubes in /scratch/\$USER/overnight/analysis/"
ls -l /scratch/$USER/overnight/analysis/${SUN}_ch{84-85,125-126,169-170,187-188}*.npz 2>/dev/null || true
