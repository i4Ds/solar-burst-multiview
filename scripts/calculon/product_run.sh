#!/bin/bash
# One image product of one MWA burst observation: coarse channel CH, a time window,
# a time resolution, one calibrator; P-AIRCARS self-cal, no AOFlagger anywhere.
# Generalises event_image.sh (one 4 s image at the light-curve maximum) to series and
# other channels or calibrators, as requested from the image board.
#
#   PRODUCT  <SUN>_ch<CH>_<LABEL>, set here
#   SUN SUN_JOB CAL CAL_JOB DATEDIR   observation, its ASVO job, calibrator, its ASVO job, YYYYMMDD
#   CH       coarse channel (default 127)
#   TRANGE   P-AIRCARS --timerange; empty = 4 s at the MWA light-curve maximum (event_peak.py)
#   TRES     image time resolution in s (default 4)
#   LABEL    product label (default peak4s); the calibrator is part of the work dir, so
#            the same channel with another calibrator is recalibrated from scratch
#   REQUEST  id of the board request this run answers (optional)
#
# Steps: wait for both tars (asvo-watch) | Birli of CH at 0.25 s, --no-rfi | calibrator MSs |
# MWA dynamic spectrum of CH (and the window, if TRANGE is empty) | P-AIRCARS (burst_series.sh).
# Registry: ~/mwa/products/<PRODUCT>.json (parameters, state, attempts), log ~/mwa/products/<PRODUCT>.md
# (one section per attempt). Runs detached on the login node (only waits and submits).
set -uo pipefail
: "${SUN:?}" "${SUN_JOB:?}" "${CAL:?}" "${CAL_JOB:?}" "${DATEDIR:?}"
CH=${CH:-127}; TRES=${TRES:-4}; LABEL=${LABEL:-peak4s}; TRANGE=${TRANGE:-}; REQUEST=${REQUEST:-}
PRODUCT=${SUN}_ch${CH}_${LABEL}
NAS=${NAS:-/mnt/nas05/data02/MWA_data/data/mwa_data2}
PR=$HOME/mwa/products
W=/scratch/$USER/mwa/events/$SUN
P=/scratch/$USER/paircars
MS=$W/${SUN}_ch${CH}_0.25s.ms
CALDIR=$P/data/${CAL}_${CAL_JOB}
TAG=${SUN}_ch${CH}_c${CAL}
CHP=$(printf %03d $((10#$CH)))   # gpubox names are zero-padded: _ch097_
ST=$PR/$PRODUCT.md
log() { echo "- $(date '+%F %H:%M') $*" | tee -a "$ST"; }
waitjob() { while squeue -M calc-cpu -h -j "$1" 2>/dev/null | grep -q .; do sleep 60; done; }
sub() { sbatch -M calc-cpu --parsable "$@" | cut -d';' -f1; }
ondisk() { grep -qE "^ *$1 .*on NAS" ~/mwa/asvo-watch.status 2>/dev/null; }
# SUN_JOB/CAL_JOB=auto: the newest ASVO job of that obsid and kind that asvo-watch reports on the NAS
jobof() { awk -v o="$1" -v k="$2" '$2 == o && $3 == k && /on NAS/ {j = $1} END {print j}' ~/mwa/asvo-watch.status 2>/dev/null; }
reg() {  # update the registry entry: reg key=value ...
  python3 - "$PR/$PRODUCT.json" "$@" <<'EOF'
import json, os, sys, time
f, kv = sys.argv[1], dict(a.split("=", 1) for a in sys.argv[2:])
d = json.load(open(f)) if os.path.exists(f) else {"attempts": []}
if kv.pop("new_attempt", None):
    d["attempts"].append({"start": time.strftime("%Y-%m-%d %H:%M")})
if "result" in kv and d["attempts"]:
    d["attempts"][-1].update(end=time.strftime("%Y-%m-%d %H:%M"), result=kv["result"])
d.update(kv)
json.dump(d, open(f + ".tmp", "w"), indent=1); os.replace(f + ".tmp", f)
EOF
}
fail() { log "FAILED: $*"; reg state=failed "result=failed: $*"; exit 1; }

mkdir -p "$W" "$PR/logs"
exec 9>"$PR/logs/$PRODUCT.lock"; flock -n 9 || { echo "product $PRODUCT is already running"; exit 1; }
echo -e "\n## attempt $(date '+%F %H:%M'): ch $CH, calibrator $CAL, ${TRANGE:-window from light curve}, $TRES s" >> "$ST"
reg new_attempt=1 product=$PRODUCT sun=$SUN sun_job=$SUN_JOB cal=$CAL cal_job=$CAL_JOB ch=$CH \
    datedir=$DATEDIR label=$LABEL tres=$TRES request=$REQUEST tag=$TAG state=waiting

while [[ $SUN_JOB == auto || $CAL_JOB == auto ]]; do
  [[ $SUN_JOB == auto ]] && j=$(jobof "$SUN" vis) && [[ -n $j ]] && SUN_JOB=$j
  [[ $CAL_JOB == auto ]] && j=$(jobof "$CAL" ms) && [[ -n $j ]] && CAL_JOB=$j
  [[ $SUN_JOB == auto || $CAL_JOB == auto ]] && sleep 600
done
CALDIR=$P/data/${CAL}_${CAL_JOB}
reg sun_job=$SUN_JOB cal_job=$CAL_JOB
until ondisk "$SUN_JOB" && ondisk "$CAL_JOB"; do sleep 600; done
log "tars on the NAS (ASVO jobs $SUN_JOB, $CAL_JOB)"; reg state=preparing

j1= j2=
stages="extract convert"   # skip the tar scan when this channel is already extracted
compgen -G "$W/${SUN}_*_ch${CHP}_*.fits" >/dev/null && [[ -f $W/${SUN}.metafits ]] && stages=convert
[[ -d $MS ]] || j1=$(sub -o "$PR/logs/birli_${SUN}_ch${CH}_%j.log" \
  --export=ALL,OBSID=$SUN,CH=$CH,TAR=$NAS/${SUN}_${SUN_JOB}_vis.tar,W=$W,STAGES="$stages" ~/mwa/flare/raw-birli.sbatch)
[[ -f $CALDIR/EXTRACT_OK ]] || j2=$(sub -o "$PR/logs/extract_${CAL}_%j.log" \
  --export=ALL,OBSID=$CAL,TAR=$NAS/${CAL}_${CAL_JOB}_ms.tar,DEST=$CALDIR ~/overnight/bin/extract-all.sbatch)
log "Birli job ${j1:-skipped (MS exists)}, calibrator extraction ${j2:-skipped}"
[[ -n $j1 ]] && waitjob "$j1"
[[ -n $j2 ]] && waitjob "$j2"
[[ -d $MS ]] || fail "no MS from Birli, see $PR/logs/birli_${SUN}_ch${CH}_*.log"
[[ -f $CALDIR/EXTRACT_OK ]] || fail "calibrator extraction, see $PR/logs/extract_${CAL}_*.log"
# per-channel MSs (picket-fence conversions) or one MS with all channels (contiguous Ch121-type)
if [[ ! -d $CALDIR/${CAL}_ch${CH}.ms ]] && [[ $(ls -d "$CALDIR"/*.ms 2>/dev/null | wc -l) -ne 1 ]]; then
  fail "calibrator $CAL has no MS for channel $CH"
fi
rm -f "$W"/${SUN}_*_ch${CHP}_*.fits
log "MS $(du -sh "$MS" | cut -f1); calibrator $(ls -d "$CALDIR"/*.ms | wc -l) MS"

# MWA dynamic spectrum of this channel (light curve for the board; window if none given)
if [[ ! -s $W/dynspec_ch$CH.npz || -z $TRANGE ]]; then
  j=$(sub -p cpu-daily --time=01:00:00 -n1 -c4 --mem=16G -J dynspec-$SUN -o "$PR/logs/dynspec_${SUN}_ch${CH}_%j.log" \
    --wrap "source \$HOME/mwa/mwa-env.sh; R(){ singularity exec --bind /scratch \$MWA_DEMO_SIF \"\$@\"; }; \
    [[ -s $W/dynspec_ch$CH.npz ]] || R python3 \$HOME/mwa/flare/dynspec.py $W/dynspec_ch$CH.npz $MS; \
    R python3 \$HOME/mwa/events/event_peak.py $W/dynspec_ch$CH.npz $PR/${SUN}_ch${CH}_lightcurve.png > $W/peak_ch$CH.txt")
  waitjob "$j"
fi
if [[ -z $TRANGE ]]; then
  TRANGE=$(sed -n 's/^TRANGE=//p' "$W/peak_ch$CH.txt")
  [[ -n $TRANGE ]] || fail "no window from the light curve, see $PR/logs/dynspec_${SUN}_ch${CH}_*.log"
  log "4 s window $TRANGE ($(sed -n 's/^PEAK=//p' "$W/peak_ch$CH.txt"))"
fi
reg state=imaging trange="$TRANGE"

SRC_MS=$MS METAFITS=$W/${SUN}.metafits TAG=$TAG TRANGE=$TRANGE TRES=$TRES SUN=$SUN CAL=$CAL \
  CALDIR=$CALDIR DATEDIR=$DATEDIR LABEL=$LABEL MEMFRAC=0.10 WALL=12:00:00 \
  bash ~/overnight/bin/burst_series.sh
img=$(ls -d "$P/out/$TAG/$DATEDIR/${SUN}_target"/imagedir_*_"$LABEL" 2>/dev/null | head -1)
n=$(ls "$img"/pbcor_hpcs/*.fits 2>/dev/null | wc -l)
[[ $n -gt 0 ]] || fail "P-AIRCARS, see ~/overnight/${TAG}_$LABEL.md"
log "DONE: $n image(s) in $img/pbcor_hpcs"
reg state=done imgdir="$img/pbcor_hpcs" n_images=$n "result=done: $n images"
~/mwa/tools-venv/bin/python ~/mwa/events/export_board.py >> "$PR/logs/export.log" 2>&1 || true
