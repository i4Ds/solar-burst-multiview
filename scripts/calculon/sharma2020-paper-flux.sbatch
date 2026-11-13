#!/bin/bash
# Oberoi 2017 S_odot on the 2015-12-03 quiet scan (Fig. 4).
# Default MS is the 10 s calibrated set, which WSClean is not using.
# After the WSClean array finishes, rerun with USE_FULL_MS=1 on the 0.5 s MS.
#
#   sbatch -M calc-cpu ~/mwa/sharma2020/sharma2020-paper-flux.sbatch
#   sbatch -M calc-cpu --dependency=afterany:168583 --export=ALL,USE_FULL_MS=1 \
#     ~/mwa/sharma2020/sharma2020-paper-flux.sbatch
#
#SBATCH --job-name=so2020-flux
#SBATCH --partition=cpu-daily
#SBATCH --time=02:00:00
#SBATCH -n1 -c4 --mem=16G
#SBATCH --array=0-3
#SBATCH --output=/home2/andre_csillaghy/mwa/logs/%x_%A_%a.log

set -euo pipefail
source "$HOME/mwa/mwa-env.sh"

BANDS=(
  "108 108MHz 1133149192-084-085"
  "162 161MHz 1133149192-125-126"
  "217 217MHz 1133149192-169-170"
  "240 239MHz 1133149192-187-188"
)
idx="${SLURM_ARRAY_TASK_ID:-0}"
read -r LABEL BANDDIR STEM <<< "${BANDS[$idx]}"

ROHIT=/mnt/nas05/data02/rohit/20151203_MWA/new_ms
if [[ "${USE_FULL_MS:-0}" == "1" ]]; then
  MS="$ROHIT/$BANDDIR/${STEM}.ms"
  TAG=full
else
  MS="$ROHIT/$BANDDIR/${STEM}_Sun_10s_cal.ms"
  TAG=10s
fi
OUT=/scratch/$USER/mwa/sharma2020/paper/flux
CODE="${PAPER_CODE:-$HOME/mwa/sharma2020}"
mkdir -p "$OUT" "$HOME/mwa/logs"

echo "node=$(hostname) label=$LABEL tag=$TAG ms=$MS"
du -sh "$MS"

run() {
  singularity exec --bind /scratch,/mnt/nas05 \
    --env OPENBLAS_NUM_THREADS=1 \
    --env PYTHONPATH="$CODE" \
    "$MWA_DEMO_SIF" python3 "$CODE/sharma2020_oberoi_flux.py" "$@"
}

run "$MS" "$OUT/${LABEL}MHz_${TAG}.json"
echo "PAPER_FLUX_OK $LABEL $TAG"
