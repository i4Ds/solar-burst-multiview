#!/bin/bash
# Quiet Sun of Sharma & Oberoi (2020) with our pipeline, unattended:
# download the two ASVO conversions -> extract coarse channel 113 (144.6 MHz)
# -> P-AIRCARS (3C444 + self-cal, one image over the observation) -> cube + PNG.
# Runs detached on the login node:
#   setsid nohup bash ~/overnight/bin/quiet2015_chain.sh > ~/overnight/quiet2015_chain.log 2>&1 < /dev/null &
# Status: ~/overnight/quiet2015_chain.md (and mail at each stage).
# ASVO jobs (14 Oct 2026; 4 s, 160 kHz, 80 kHz edges, AOFlagger off):
#   1113526  1133149192  Sun, 2015-12-03 03:39:35-03:44:31   24.4 GiB
#   1113527  1133161488  3C444, 2015-12-03 07:04:31           9.0 GiB
set -uo pipefail
MAIL=andre.csillaghy@fhnw.ch
BIN=$HOME/overnight/bin
DL=/mnt/nas05/data02/MWA_data/data/mwa_data2
W=/scratch/$USER/mwa/quiet2015
CH=${CH:-113}
SUN=1133149192; SUNJOB=1113526; SUNBYTES=26092141363   # 24.3 GiB, lower bound
CAL=1133161488; CALJOB=1113527; CALBYTES=9556302234    #  8.9 GiB, lower bound
ST=$HOME/overnight/quiet2015_chain.md
log() { echo "- $(date '+%Y-%m-%d %H:%M') $*" | tee -a "$ST"; }
notify() { sbatch -M calc-cpu -p cpu-daily --time=00:01:00 -n1 -c1 --mem=50M -J "quiet2015: ${*:0:90}" \
  -o /dev/null --mail-type=END --mail-user=$MAIL --wrap true >/dev/null 2>&1 || true; log "$*"; }
waitjob() { while squeue -M calc-cpu -h -j "$1" 2>/dev/null | grep -q .; do sleep 60; done; }
jid() { awk '{print $4}'; }

# FROM=pcars skips download and extraction (already done).
FROM=${FROM:-download}
echo "# quiet2015 chain, started $(date '+%Y-%m-%d %H:%M') (ch$CH, from $FROM)" >> "$ST"
cd "$HOME/mwa" || exit 1
if [[ $FROM == download ]]; then

# 1. downloads (both in parallel; each resumes until the tar has the expected size)
j1=$(sbatch -M calc-cpu --export=ALL,JOBID=$SUNJOB,OBSID=$SUN,KIND=ms,BYTES=$SUNBYTES,DEST=$DL \
     -o logs/asvo-dl-$SUN-%j.out ~/mwa/asvo-download-retry.sbatch | jid)
j2=$(sbatch -M calc-cpu --export=ALL,JOBID=$CALJOB,OBSID=$CAL,KIND=ms,BYTES=$CALBYTES,DEST=$DL \
     -o logs/asvo-dl-$CAL-%j.out ~/mwa/asvo-download-retry.sbatch | jid)
log "download jobs $j1 (Sun) and $j2 (3C444) submitted"
waitjob "$j1"; waitjob "$j2"
for o in $SUN $CAL; do
  grep -q DOWNLOAD_OK logs/asvo-dl-$o-*.out 2>/dev/null || { notify "download of $o failed, see ~/mwa/logs/asvo-dl-$o-*.out"; exit 1; }
done
notify "downloads done ($SUN, $CAL)"

# 2. extract the metafits and the MS holding coarse channel $CH from each tar
j=$(sbatch -M calc-cpu -p cpu-daily --time=02:00:00 -n1 -c1 --mem=2G -J extract-quiet2015 -o logs/%x_%j.log --wrap "
set -e
for o in $SUN $CAL; do
  t=\$(ls $DL/\${o}_*_ms.tar | head -1); d=$W/\$o; mkdir -p \$d; cd \$d
  tar -tf \$t > members.txt
  m=\$(grep -E 'ch0*$CH([^0-9]|\$)|[-_]0*$CH-' members.txt | grep -E '\.ms/?\$' | head -1)
  [ -n \"\$m\" ] || m=\$(grep -E '\.ms/?\$' members.txt | grep -E '0*$CH' | head -1)
  echo \"\$o: \$m\"
  tar -xf \$t ./\${o}.metafits \"\$m\" 2>/dev/null || tar -xf \$t \${o}.metafits \"\$m\"
done
ls -R $W | head -40; echo EXTRACT_OK" | jid)
waitjob "$j"
grep -q EXTRACT_OK logs/extract-quiet2015_$j.log || { notify "extraction failed, see ~/mwa/logs/extract-quiet2015_$j.log"; exit 1; }
log "extraction done"
fi
SUNMS=$(ls -d $W/$SUN/*.ms | head -1); CALMS=$(ls -d $W/$CAL/*.ms | head -1)

# 3. P-AIRCARS: calibrator dir with only this channel, then one image over the observation
CALDIR=/scratch/$USER/paircars/data/${CAL}_ch$CH
mkdir -p "$CALDIR"; cp -a "$CALMS" "$W/$CAL/$CAL.metafits" "$CALDIR/"
notify "starting P-AIRCARS"
SUN=$SUN CAL=$CAL CALDIR=$CALDIR DATEDIR=20151203 SRC_MS=$SUNMS METAFITS=$W/$SUN/$SUN.metafits \
  TAG=${SUN}_ch$CH TRANGE="2015/12/03/03:39:44~2015/12/03/03:44:24" TRES=280 LABEL=quiet \
  bash "$BIN/burst_series.sh" > "$HOME/overnight/${SUN}_ch${CH}_quiet.log" 2>&1
tail -3 "$HOME/overnight/${SUN}_ch${CH}_quiet.md" >> "$ST"
notify "chain finished; see ~/overnight/${SUN}_ch${CH}_quiet.md"
