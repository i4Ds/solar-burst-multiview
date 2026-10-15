#!/bin/bash
# Longer quiet Sun at 137.0 MHz (ch107) on 2022-09-30 (03:20-03:33, three observations),
# imaged with the 2022 and with the 2015 imaging settings, to find why the 2022 quiet
# disk is fainter than the 2015 one (Sharma & Oberoi 2020). Runs detached on the login node:
#   setsid nohup bash ~/overnight/bin/quiet2022_long.sh > ~/overnight/quiet2022_long.log 2>&1 < /dev/null &
# Status: ~/overnight/quiet2022_long.md
set -uo pipefail
BIN=$HOME/overnight/bin
A=/mnt/nas05/data02/MWA_data/data/mwa_data
Q=/scratch/$USER/mwa/flare20220930_quiet
CAL=1348522216; CALDIR=/scratch/$USER/paircars/data/${CAL}_ch107
OUT=/scratch/$USER/overnight/quiet2022_long
ST=$HOME/overnight/quiet2022_long.md
log() { echo "- $(date '+%Y-%m-%d %H:%M') $*" | tee -a "$ST"; }
waitjob() { while squeue -M calc-cpu -h -j "$1" 2>/dev/null | grep -q .; do sleep 60; done; }
declare -A TR=(
  [1348543128]="2022/09/30/03:20:08~2022/09/30/03:23:16"
  [1348543424]="2022/09/30/03:23:36~2022/09/30/03:28:12"
  [1348543720]="2022/09/30/03:28:32~2022/09/30/03:33:08"
)
declare -A TS=([1348543128]=192 [1348543424]=280 [1348543720]=280)   # one image per range
echo "# quiet2022_long, started $(date '+%Y-%m-%d %H:%M')" > "$ST"
cd "$HOME/mwa" || exit 1

# 1. ch107 + metafits of the two earlier observations
j=$(sbatch -M calc-cpu -p cpu-daily --time=01:00:00 -n1 -c1 --mem=2G -J extract-q22 -o logs/%x_%j.log --wrap "
set -e; cd $Q
for o in 1348543128 1348543424; do
  [ -d \${o}_ch107.ms ] || tar -xf \$(ls $A/\${o}_*_ms.tar) ./\${o}.metafits ./\${o}_ch107.ms
done
ls $Q; echo EXTRACT_OK" | awk '{print $4}')
waitjob "$j"
grep -q EXTRACT_OK logs/extract-q22_$j.log || { log "extraction failed (logs/extract-q22_$j.log)"; exit 1; }
log "extracted ch107 of 1348543128 and 1348543424"

# 2. P-AIRCARS on each observation, keeping the calibrated MS
pids=()
for o in "${!TR[@]}"; do
  SUN=$o CAL=$CAL CALDIR=$CALDIR SRC_MS=$Q/${o}_ch107.ms METAFITS=$Q/$o.metafits TAG=${o}_ch107_long \
    TRANGE="${TR[$o]}" TRES=${TS[$o]} LABEL=long EXTRA=--keep_calibrated_ms \
    bash "$BIN/burst_series.sh" > "$HOME/overnight/${o}_ch107_long_long.log" 2>&1 &
  pids+=($!); sleep 120
done
wait "${pids[@]}"
for o in "${!TR[@]}"; do log "$o: $(tail -1 $HOME/overnight/${o}_ch107_long_long.md)"; done
MSS=()
for o in 1348543128 1348543424 1348543720; do
  m=$(ls -d /scratch/$USER/paircars/out/${o}_ch107_long/20220930/${o}_target/calibrated_ms/*ch_107*.ms 2>/dev/null | head -1)
  [[ -n $m ]] && MSS+=("$m") || log "no calibrated MS for $o"
done
[[ ${#MSS[@]} -gt 0 ]] || exit 1
ILOG=$(ls /scratch/$USER/paircars/work/1348543720_ch107_long/20220930/*_target/logs/imaging_1348543720_ch_107.log | head -1)

# 3. four images: 1348543720 alone and all three, with 2022 and 2015 settings
j=$(sbatch -M calc-cpu --export=ALL,ILOG=$ILOG,OUT=$OUT,MSS="${MSS[*]}" "$BIN/quiet_settings.sbatch" | awk '{print $4}')
log "imaging job $j (${#MSS[@]} observations)"
waitjob "$j"
if grep -q SETTINGS_OK logs/quiet-settings_$j.log; then log "done: images in $OUT"
else log "imaging failed (logs/quiet-settings_$j.log)"; fi
