#!/bin/bash
# 0.5 s WSClean snapshot (mid-scan) with the published CASA geometry.
# Fallback if paircars tclean segfaults on the 35 GB MS. Not the paper's
# imager; same 1024 / 50″ / Briggs 0 / Hogbom 2500. Writes paper/wsclean/.
#
#   sbatch -M calc-cpu ~/mwa/sharma2020/sharma2020-paper-wsclean-snap.sbatch
#
#SBATCH --job-name=so2020-wsnap
#SBATCH --partition=cpu-daily
#SBATCH --time=04:00:00
#SBATCH -n1 -c8 --mem=48G
#SBATCH --array=0-3
#SBATCH --output=/home2/andre_csillaghy/mwa/logs/%x_%A_%a.log

set -euo pipefail
source "$HOME/mwa/mwa-env.sh"

BANDS=(
  "108 108MHz 1133149192-084-085.ms"
  "162 161MHz 1133149192-125-126.ms"
  "217 217MHz 1133149192-169-170.ms"
  "240 239MHz 1133149192-187-188.ms"
)
idx="${SLURM_ARRAY_TASK_ID:-0}"
read -r LABEL BANDDIR MSNAME <<< "${BANDS[$idx]}"

ROHIT=/mnt/nas05/data02/rohit/20151203_MWA/new_ms
MS="$ROHIT/$BANDDIR/$MSNAME"
OUT=/scratch/$USER/mwa/sharma2020/paper/wsclean
NAME="$OUT/${LABEL}MHz_mid"
mkdir -p "$OUT" "$HOME/mwa/logs"
TMP="$OUT/tmp-$LABEL"
mkdir -p "$TMP"

run() {
  singularity exec --bind /scratch,/mnt/nas05 \
    --env OPENBLAS_NUM_THREADS=1 \
    "$MWA_DEMO_SIF" "$@"
}

# 4 min / 0.5 s = 480–570 intervals depending on how the MS is counted.
# Mid of the published window: interval 285.
INTERVAL="${INTERVAL:-285}"
sunpos="16h40m55.28s -19d40m25.38s"
echo "node=$(hostname) label=$LABEL interval=$INTERVAL ms=$MS"
du -sh "$MS"

run wsclean \
  -name "$NAME" \
  -temp-dir "$TMP" \
  -data-column CORRECTED_DATA \
  -shift $sunpos \
  -size 1024 1024 -scale 50asec \
  -pol I -weight briggs 0 \
  -niter 2500 -gain 0.1 -mgain 0.85 \
  -interval "$INTERVAL" $((INTERVAL + 1)) \
  -no-update-model-required \
  -j "${SLURM_CPUS_PER_TASK}" \
  "$MS"
rm -rf "$TMP"
ls -lh "$NAME"-*.fits
echo "PAPER_WSCLEAN_SNAP_OK $LABEL"
