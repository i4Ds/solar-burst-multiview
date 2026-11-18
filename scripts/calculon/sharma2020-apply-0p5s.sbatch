#!/bin/bash
# Apply the existing Cen A bandpass to the 0.5 s Sun visibilities.
# No time averaging. No imaging.
#
#   sbatch -M calc-cpu ~/mwa/sharma2020/sharma2020-apply-0p5s.sbatch
#
#SBATCH --job-name=so2020-0p5s-cal
#SBATCH --partition=cpu-daily
#SBATCH --time=08:00:00
#SBATCH -n1 -c4 --mem=64G
#SBATCH --array=0-7
#SBATCH --output=/home2/andre_csillaghy/mwa/logs/%x_%A_%a.log
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=andre.csillaghy@fhnw.ch

set -euo pipefail
source "$HOME/paircars/env.sh"

CHANS=(84 85 125 126 169 170 187 188)
idx="${SLURM_ARRAY_TASK_ID:-0}"
CH="${CHANS[$idx]}"
CODE="${PAPER_CODE:-$HOME/mwa/sharma2020}"
OUT=/scratch/$USER/mwa/sharma2020/raw/cal_0p5s
mkdir -p "$OUT" "$OUT/tmp-$CH"
export TMPDIR="$OUT/tmp-$CH" TMP="$TMPDIR" TEMP="$TMPDIR"
export OPENBLAS_NUM_THREADS=1
cd "$OUT"

echo "node=$(hostname) ch=$CH"
python "$CODE/apply_0p5s_bcal.py" "$CH"
echo "DONE ch$CH"
