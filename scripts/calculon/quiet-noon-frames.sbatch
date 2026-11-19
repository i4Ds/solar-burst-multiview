#!/bin/bash
# SuperUniform 0.5 s frames for the 4 December 2015 noon control.
# Same CASA numbers as Figure 4. Phase centre from this metafits.
#
#   sbatch -M calc-cpu ~/mwa/sharma2020/quiet-noon-frames.sbatch
#
#SBATCH --job-name=qn-frames
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

SUN_OBS="${SUN_OBS:-1133236216}"
SCRATCH="/scratch/$USER/mwa/quiet_noon"
MS="$SCRATCH/cal_0p5s_casa/${SUN_OBS}_ch${PAIR}_0p5s.ms"
META="$SCRATCH/${SUN_OBS}/${SUN_OBS}.metafits"
OUT="$SCRATCH/casa_su"
CODE="${PAPER_CODE:-$HOME/mwa/sharma2020}"
export PYTHONPATH="$CODE"
export OPENBLAS_NUM_THREADS=1

mkdir -p "$OUT" "$OUT/tmp-$LABEL"
export TMPDIR="$OUT/tmp-$LABEL" TMP="$TMPDIR" TEMP="$TMPDIR"
cd "$OUT"

echo "node=$(hostname) label=$LABEL pair=$PAIR"
python "$CODE/quiet_noon_casa_snap.py" \
  "$MS" "$OUT/${LABEL}MHz" \
  --metafits "$META" --all-frames
echo "QN_FRAMES_OK $LABEL"
