#!/bin/bash
# All 570 half-second CASA frames for one Fig. 4 band (SuperUniform, 8000).
# Figure 4 is the time mean of these, not one mid-scan snapshot.
# Writes only under /scratch/$USER/mwa/sharma2020/paper/casa_su/.
#
#   sbatch -M calc-cpu ~/mwa/sharma2020/sharma2020-paper-casa.sbatch
#
#SBATCH --job-name=so2020-casa
#SBATCH --partition=cpu-daily
#SBATCH --time=23:59:00
#SBATCH -n1 -c8 --mem=48G
#SBATCH --array=0-3
#SBATCH --output=/home2/andre_csillaghy/mwa/logs/%x_%A_%a.log

set -euo pipefail
source "$HOME/paircars/env.sh"

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
OUT=/scratch/$USER/mwa/sharma2020/paper/casa_su
CODE="${PAPER_CODE:-$HOME/mwa/sharma2020}"
START="${START:-0}"
STOP="${STOP:-570}"
mkdir -p "$OUT" "$HOME/mwa/logs" "$OUT/tmp-$LABEL"

export TMPDIR="$OUT/tmp-$LABEL"
export TMP="$TMPDIR"
export TEMP="$TMPDIR"
export OPENBLAS_NUM_THREADS=1
cd "$OUT"

echo "node=$(hostname) label=$LABEL frames=${START}-${STOP} ms=$MS"
du -sh "$MS"
python -c "import casatasks; print('casa-ok', casatasks.__file__)"

python "$CODE/sharma2020_casa_snap.py" \
  "$MS" "$OUT/${LABEL}MHz" \
  --all-frames --start "$START" --stop "$STOP"

echo "PAPER_CASA_ALL_OK $LABEL"
