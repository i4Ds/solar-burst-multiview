#!/bin/bash
# 570 half-second SuperUniform maps from the archive visibilities after
# CASA applycal of Rohit's Cen A bandpass. No P-AIRCARS.
# Figure 4 is the time mean of these frames.
#
#   sbatch -M calc-cpu ~/mwa/sharma2020/sharma2020-raw-rohit-frames.sbatch
#
#SBATCH --job-name=so2020-raw-rohit
#SBATCH --partition=cpu-daily
#SBATCH --time=23:59:00
#SBATCH -n1 -c8 --mem=48G
#SBATCH --array=0-3
#SBATCH --output=/home2/andre_csillaghy/mwa/logs/%x_%A_%a.log
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=andre.csillaghy@fhnw.ch

set -euo pipefail
source "$HOME/paircars/env.sh"

BANDS=(
  "108 84-85"
  "162 125-126"
  "217 169-170"
  "240 187-188"
)
idx="${SLURM_ARRAY_TASK_ID:-0}"
read -r LABEL PAIR <<< "${BANDS[$idx]}"

MS=/scratch/$USER/mwa/sharma2020/raw/cal_0p5s_casa/1133149192_ch${PAIR}_0p5s.ms
OUT=/scratch/$USER/mwa/sharma2020/raw/casa_su_rohitcal
CODE="${PAPER_CODE:-$HOME/mwa/sharma2020}"
START="${START:-0}"
STOP="${STOP:-570}"

mkdir -p "$OUT" "$OUT/tmp-$LABEL"
export TMPDIR="$OUT/tmp-$LABEL" TMP="$TMPDIR" TEMP="$TMPDIR"
export OPENBLAS_NUM_THREADS=1
cd "$OUT"

echo "node=$(hostname) label=$LABEL pair=$PAIR frames=${START}-${STOP}"
du -sh "$MS"
python -c "import casatasks; print('casa-ok', casatasks.__file__)"

python "$CODE/sharma2020_casa_snap.py" \
  "$MS" "$OUT/${LABEL}MHz" \
  --all-frames --start "$START" --stop "$STOP"

echo "RAW_ROHIT_FRAMES_OK $LABEL"
