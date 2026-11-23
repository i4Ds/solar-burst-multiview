#!/bin/bash
# Mohan mean T_B for 3 December 2015 03:49 (noon pick 1133149792).
# Rohit's calibrated MS and FITS. Haslam at this pointing, not Table 1.
# Does not modify Rohit's tree.
#
#   sbatch -M calc-cpu ~/mwa/sharma2020/quiet-dec3-noon-mean.sbatch
#
#SBATCH --job-name=qd3-noon-mean
#SBATCH --partition=cpu-daily
#SBATCH --time=02:00:00
#SBATCH -n1 -c4 --mem=16G
#SBATCH --array=0-3
#SBATCH --output=/home2/andre_csillaghy/mwa/logs/%x_%A_%a.log
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=andre.csillaghy@fhnw.ch

set -euo pipefail
source "$HOME/paircars/env.sh"

BANDS=(
  "108 084-085 108MHz"
  "162 125-126 161MHz"
  "217 169-170 217MHz"
  "240 187-188 239MHz"
)
idx="${SLURM_ARRAY_TASK_ID:-0}"
read -r LABEL PAIR DIR <<< "${BANDS[$idx]}"

OBS=1133149792
ROHIT=/mnt/nas05/data02/rohit/20151203_MWA/new_ms
MS="$ROHIT/${DIR}/${OBS}_${PAIR}.ms"
FITSDIR="$ROHIT/fits"
OUTDIR=/scratch/$USER/mwa/quiet_noon/${OBS}/mean_tb
CODE="${PAPER_CODE:-$HOME/mwa/sharma2020}"
export PYTHONPATH="$CODE"
HASLAM="$HOME/mwa/data/haslam/lambda_haslam408_nofilt.fits"
TIME=2015-12-03T03:52:03

mkdir -p "$OUTDIR" "$CODE/data/haslam"
if [[ -f "$HASLAM" && ! -f "$CODE/data/haslam/lambda_haslam408_nofilt.fits" ]]; then
  cp -n "$HASLAM" "$CODE/data/haslam/" || true
fi

echo "node=$(hostname) label=$LABEL ms=$MS"
JSON="$OUTDIR/${LABEL}MHz_flux.json"
python "$CODE/sharma2020_oberoi_flux.py" "$MS" "$JSON" \
  --column CORRECTED_DATA --sky haslam --time "$TIME" --haslam "$HASLAM"
S_JY=$(python -c "import json; print(float(json.load(open('$JSON'))['s_odot_sfu'])*1e4)")
echo "S_odot ${LABEL} MHz = ${S_JY} Jy"
python "$CODE/quiet_noon_mean_tb.py" \
  "$FITSDIR/${OBS}_${PAIR}.*.image.FITS" \
  "$OUTDIR/${LABEL}MHz_tb.npz" \
  --s-odot-jy "$S_JY"
echo "QD3_NOON_MEAN_OK $LABEL"
