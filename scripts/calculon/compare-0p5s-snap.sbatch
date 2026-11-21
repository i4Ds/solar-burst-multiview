#!/bin/bash
#SBATCH --job-name=so2020-0p5s-cmp
#SBATCH --partition=cpu-daily
#SBATCH --time=02:00:00
#SBATCH -n1 -c8 --mem=48G
#SBATCH --output=/home2/andre_csillaghy/mwa/logs/%x_%j.log
#SBATCH --mail-type=NONE

set -euo pipefail
source "$HOME/paircars/env.sh"
CODE="${PAPER_CODE:-$HOME/mwa/sharma2020}"
OUT=/scratch/$USER/mwa/sharma2020/raw/cal_0p5s_casa
mkdir -p "$OUT/tmp-cmp"
export TMPDIR="$OUT/tmp-cmp" TMP="$TMPDIR" TEMP="$TMPDIR"
export OPENBLAS_NUM_THREADS=1
python "$CODE/compare_0p5s_snap.py"
