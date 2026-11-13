#!/bin/bash
# Image Sharma & Oberoi 2020 Fig. 4 bands from Rohit's calibrated MS.
# One MFS image over the full 4 min quiet scan (1133149192), per band.
# Geometry from the published CASA FITS: 1024 px, 50", Briggs 0, Hogbom.
#
#   sbatch -M calc-cpu scripts/calculon/sharma2020-fig4.sbatch
#   # or a single band:
#   sbatch -M calc-cpu --export=ALL,SLURM_ARRAY_TASK_ID=0 scripts/calculon/sharma2020-fig4.sbatch
#
#SBATCH --job-name=so2020-fig4
#SBATCH --partition=cpu-daily
#SBATCH --time=08:00:00
#SBATCH -n1 -c8 --mem=48G
#SBATCH --array=0-3
#SBATCH --output=/home2/andre_csillaghy/mwa/logs/%x_%A_%a.log

set -euo pipefail
source "$HOME/mwa/mwa-env.sh"

# label  banddir  ms-stem
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
OUT=/scratch/$USER/mwa/sharma2020/fig4
NAME="$OUT/${LABEL}MHz"
mkdir -p "$OUT" "$HOME/mwa/logs"

run() {
  singularity exec --bind /scratch,/mnt/nas05 \
    --env OPENBLAS_NUM_THREADS=1 \
    "$MWA_DEMO_SIF" "$@"
}

echo "node=$(hostname) label=$LABEL ms=$MS"
du -sh "$MS"
run wsclean -version | head -2

# Phase centre of the published CASA images (clean.last / FITS CRVAL).
# Do not recompute from get_body: ICRS vs apparent Sun is ~1° here.
sunpos="16h40m55.28s -19d40m25.38s"
echo "shift=$sunpos"
TMP="$OUT/tmp-$LABEL"
mkdir -p "$TMP"

# Published CASA images: 1024^2, 50", Briggs, Hogbom, niter 2500, gain 0.1.
# CORRECTED_DATA is the gain-calibrated column in these MS.
# -temp-dir must be on scratch: the Rohit tree is not writable.
run wsclean \
  -name "$NAME" \
  -temp-dir "$TMP" \
  -data-column CORRECTED_DATA \
  -shift $sunpos \
  -size 1024 1024 -scale 50asec \
  -pol I -weight briggs 0 \
  -niter 2500 -gain 0.1 -mgain 0.85 \
  -no-update-model-required \
  -j "${SLURM_CPUS_PER_TASK}" \
  "$MS"
rm -rf "$TMP"

ls -lh "$NAME"-*.fits
echo "FIG4_IMAGE_OK $LABEL"
