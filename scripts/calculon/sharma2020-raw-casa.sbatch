#!/bin/bash
# SuperUniform maps from the P-AIRCARS-calibrated Figure 4 measurement sets.
# P-AIRCARS imaging wrote an empty directory (timerange sat outside the data).
# These visibilities cover 03:39:41–03:44:25; the timerange below sits inside that.
#
#   sbatch -M calc-cpu ~/mwa/sharma2020/sharma2020-raw-casa.sbatch
#
#SBATCH --job-name=so2020-raw-casa
#SBATCH --partition=cpu-daily
#SBATCH --time=08:00:00
#SBATCH -n1 -c8 --mem=48G
#SBATCH --array=0-7
#SBATCH --output=/home2/andre_csillaghy/mwa/logs/%x_%A_%a.log
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=andre.csillaghy@fhnw.ch

set -euo pipefail
source "$HOME/paircars/env.sh"

CHANS=(84 85 125 126 169 170 187 188)
idx="${SLURM_ARRAY_TASK_ID:-0}"
CH="${CHANS[$idx]}"

MS=/scratch/$USER/paircars/out/fig4_raw/20151203/1133149192_target/calibrated_ms/target_1133149192_ch_${CH}_t_20151203033941_20151203034425.ms
OUT=/scratch/$USER/mwa/sharma2020/raw/casa_su
CODE="${PAPER_CODE:-$HOME/mwa/sharma2020}"
# Inside the unflagged span (03:39:41–03:44:25), 280 s
TRANGE="2015/12/03/03:39:44.0~2015/12/03/03:44:24.0"

mkdir -p "$OUT" "$OUT/tmp-$CH"
export TMPDIR="$OUT/tmp-$CH" TMP="$TMPDIR" TEMP="$TMPDIR"
export OPENBLAS_NUM_THREADS=1
cd "$OUT"

echo "node=$(hostname) ch=$CH ms=$MS"
du -sh "$MS"
python -c "import casatasks; print('casa-ok', casatasks.__file__)"

python "$CODE/sharma2020_casa_snap.py" \
  "$MS" "$OUT/ch${CH}" \
  --timerange "$TRANGE"

echo "RAW_CASA_OK ch$CH"
