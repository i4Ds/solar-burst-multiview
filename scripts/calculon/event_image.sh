#!/bin/bash
# One image per burst (docs/burst-imaging-plan.md): coarse channel CH (127 =
# 162.6 MHz), 4 s at the MWA maximum, P-AIRCARS self-cal, no AOFlagger.
#   1  wait until asvo-watch has both tars on the NAS (target raw vis, calibrator ms)
#   2  Birli of channel CH at 0.25 s (raw-birli.sbatch, --no-rfi) | calibrator MSs extracted
#   3  MWA dynamic spectrum of CH -> the 4 s window (event_peak.py, PNG)
#   4  P-AIRCARS on that window (burst_series.sh, TRES=4)
# It only waits and submits, so it runs detached on the login node:
#   SUN=1419137296 SUN_JOB=1114407 CAL=1419161128 CAL_JOB=1114408 DATEDIR=20241225 \
#     setsid nohup bash ~/mwa/events/event_image.sh > ~/mwa/events/logs/1419137296.out 2>&1 < /dev/null &
# Status: ~/mwa/events/<SUN>.md (no Slurm mail: it never arrives on calculon).
set -uo pipefail
: "${SUN:?}" "${SUN_JOB:?}" "${CAL:?}" "${CAL_JOB:?}" "${DATEDIR:?}"
CH=${CH:-127}
NAS=${NAS:-/mnt/nas05/data02/MWA_data/data/mwa_data2}
EV=$HOME/mwa/events
W=/scratch/$USER/mwa/events/$SUN
P=/scratch/$USER/paircars
ST=$EV/$SUN.md
MS=$W/${SUN}_ch${CH}_0.25s.ms
CALDIR=$P/data/${CAL}_${CAL_JOB}
log() { echo "- $(date '+%F %H:%M') $*" | tee -a "$ST"; }
waitjob() { while squeue -M calc-cpu -h -j "$1" 2>/dev/null | grep -q .; do sleep 60; done; }
sub() { sbatch -M calc-cpu --parsable "$@" | cut -d';' -f1; }
ondisk() { grep -qE "^ *$1 .*on NAS" ~/mwa/asvo-watch.status 2>/dev/null; }

mkdir -p "$W" "$EV/logs"
exec 9>"$EV/logs/$SUN.lock"; flock -n 9 || { echo "event_image.sh for $SUN is already running"; exit 1; }
echo "# $SUN, ch $CH, calibrator $CAL (started $(date '+%F %H:%M'))" > "$ST"

until ondisk "$SUN_JOB" && ondisk "$CAL_JOB"; do sleep 600; done
log "tars on the NAS (ASVO jobs $SUN_JOB, $CAL_JOB)"

j1= j2=
stages="extract convert"   # skip the tar scan when this channel is already extracted
compgen -G "$W/${SUN}_*_ch${CH}_*.fits" >/dev/null && [[ -f $W/${SUN}.metafits ]] && stages=convert
[[ -d $MS ]] || j1=$(sub -o "$EV/logs/birli_${SUN}_%j.log" \
  --export=ALL,OBSID=$SUN,CH=$CH,TAR=$NAS/${SUN}_${SUN_JOB}_vis.tar,W=$W,STAGES="$stages" ~/mwa/flare/raw-birli.sbatch)
[[ -f $CALDIR/EXTRACT_OK ]] || j2=$(sub -o "$EV/logs/extract_${CAL}_%j.log" \
  --export=ALL,OBSID=$CAL,TAR=$NAS/${CAL}_${CAL_JOB}_ms.tar,DEST=$CALDIR ~/overnight/bin/extract-all.sbatch)
log "Birli job ${j1:-skipped (MS exists)}, calibrator extraction ${j2:-skipped}"
[[ -n $j1 ]] && waitjob "$j1"
[[ -n $j2 ]] && waitjob "$j2"
[[ -d $MS ]] || { log "FAILED: no MS from Birli, see $EV/logs/birli_${SUN}_*.log"; exit 1; }
[[ -f $CALDIR/EXTRACT_OK ]] || { log "FAILED: calibrator extraction, see $EV/logs/extract_${CAL}_*.log"; exit 1; }
# Birli writes only the MS: keep the metafits next to it for P-AIRCARS, drop the gpubox files
rm -f "$W"/${SUN}_*_ch${CH}_*.fits
log "MS $(du -sh "$MS" | cut -f1); calibrator $(ls -d "$CALDIR"/*.ms | wc -l) MS"

j=$(sub -p cpu-daily --time=01:00:00 -n1 -c4 --mem=16G -J dynspec-$SUN -o "$EV/logs/dynspec_${SUN}_%j.log" \
  --wrap "source \$HOME/mwa/mwa-env.sh; R(){ singularity exec --bind /scratch \$MWA_DEMO_SIF \"\$@\"; }; \
  rm -f $W/dynspec_ch$CH.npz; R python3 \$HOME/mwa/flare/dynspec.py $W/dynspec_ch$CH.npz $MS && \
  R python3 \$HOME/mwa/events/event_peak.py $W/dynspec_ch$CH.npz $EV/${SUN}_ch${CH}_lightcurve.png > $W/peak.txt")
waitjob "$j"
TRANGE=$(sed -n 's/^TRANGE=//p' "$W/peak.txt")
[[ -n $TRANGE ]] || { log "FAILED: no peak window, see $EV/logs/dynspec_${SUN}_*.log"; exit 1; }
log "4 s window $TRANGE ($(sed -n 's/^PEAK=//p' "$W/peak.txt")); light curve $EV/${SUN}_ch${CH}_lightcurve.png"

SRC_MS=$MS METAFITS=$W/${SUN}.metafits TAG=${SUN}_ch${CH} TRANGE=$TRANGE TRES=4 SUN=$SUN CAL=$CAL \
  CALDIR=$CALDIR DATEDIR=$DATEDIR LABEL=peak4s MEMFRAC=0.10 WALL=12:00:00 \
  bash ~/overnight/bin/burst_series.sh
img=$(ls -d "$P/out/${SUN}_ch${CH}/$DATEDIR/${SUN}_target"/imagedir_*_peak4s 2>/dev/null | head -1)
n=$(ls "$img"/pbcor_hpcs/*.fits 2>/dev/null | wc -l)
if [[ $n -gt 0 ]]; then log "DONE: $n image(s) in $img/pbcor_hpcs"
else log "FAILED in P-AIRCARS: see ~/overnight/${SUN}_ch${CH}_peak4s.md"; exit 1; fi
# one MLflow run per image (experiment archive-bursts; UI: mlflow-ui.sh)
if ~/mwa/mlflow-venv/bin/python ~/mwa/events/log_event_mlflow.py --sun "$SUN" --cal "$CAL" --ch "$CH" \
     --datedir "$DATEDIR" >> "$EV/logs/mlflow_${SUN}.log" 2>&1; then log "logged to MLflow"
else log "MLflow logging failed, see $EV/logs/mlflow_${SUN}.log"; fi
