#!/bin/bash
# Apply Rohit's Cen A CASA bandpass to the 0.5 s Sun visibilities.
# No P-AIRCARS. No time averaging. No imaging.
#
#   sbatch -M calc-cpu ~/mwa/sharma2020/sharma2020-apply-0p5s-rohit.sbatch
#
#SBATCH --job-name=so2020-rohit-cal
#SBATCH --partition=cpu-daily
#SBATCH --time=08:00:00
#SBATCH -n1 -c4 --mem=64G
#SBATCH --array=0-3
#SBATCH --output=/home2/andre_csillaghy/mwa/logs/%x_%A_%a.log
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=andre.csillaghy@fhnw.ch

set -euo pipefail
source "$HOME/paircars/env.sh"

PAIRS=(84-85 125-126 169-170 187-188)
idx="${SLURM_ARRAY_TASK_ID:-0}"
PAIR="${PAIRS[$idx]}"
CODE="${PAPER_CODE:-$HOME/mwa/sharma2020}"
OUT=/scratch/$USER/mwa/sharma2020/raw/cal_0p5s_casa
mkdir -p "$OUT" "$OUT/tmp-$PAIR"
export TMPDIR="$OUT/tmp-$PAIR" TMP="$TMPDIR" TEMP="$TMPDIR"
export OPENBLAS_NUM_THREADS=1
cd "$OUT"

echo "node=$(hostname) pair=$PAIR"
python "$CODE/apply_0p5s_rohit_cal.py" "$PAIR"
echo "DONE $PAIR"
