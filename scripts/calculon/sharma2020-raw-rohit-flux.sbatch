#!/bin/bash
# Oberoi 2017 S_odot on the CASA-applycal archive visibilities.
#
#   sbatch -M calc-cpu ~/mwa/sharma2020/sharma2020-raw-rohit-flux.sbatch
#
#SBATCH --job-name=so2020-raw-flux
#SBATCH --partition=cpu-daily
#SBATCH --time=02:00:00
#SBATCH -n1 -c4 --mem=16G
#SBATCH --array=0-3
#SBATCH --output=/home2/andre_csillaghy/mwa/logs/%x_%A_%a.log

set -euo pipefail
source "$HOME/mwa/mwa-env.sh"

BANDS=(
  "108 84-85"
  "162 125-126"
  "217 169-170"
  "240 187-188"
)
idx="${SLURM_ARRAY_TASK_ID:-0}"
read -r LABEL PAIR <<< "${BANDS[$idx]}"

MS=/scratch/$USER/mwa/sharma2020/raw/cal_0p5s_casa/1133149192_ch${PAIR}_0p5s.ms
OUT=/scratch/$USER/mwa/sharma2020/raw/flux_rohitcal
CODE="${PAPER_CODE:-$HOME/mwa/sharma2020}"
mkdir -p "$OUT"

echo "node=$(hostname) label=$LABEL ms=$MS"
du -sh "$MS"

run() {
  singularity exec --bind /scratch \
    --env OPENBLAS_NUM_THREADS=1 \
    --env PYTHONPATH="$CODE" \
    "$MWA_DEMO_SIF" python3 "$CODE/sharma2020_oberoi_flux.py" "$@"
}

run "$MS" "$OUT/${LABEL}MHz_full.json" --column CORRECTED_DATA --sky haslam
echo "RAW_ROHIT_FLUX_OK $LABEL"
