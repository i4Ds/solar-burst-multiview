#!/bin/bash
# 570 half-second SuperUniform maps from P-AIRCARS-calibrated Figure 4 pairs.
# Concatenate the two coarse channels of each band first (as in Rohit's MS).
# Figure 4 is the time mean of these frames, not the 280 s scan-mean maps.
#
#   sbatch -M calc-cpu ~/mwa/sharma2020/sharma2020-raw-casa-frames.sbatch
#
#SBATCH --job-name=so2020-raw-frames
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
  "108 84 85"
  "162 125 126"
  "217 169 170"
  "240 187 188"
)
idx="${SLURM_ARRAY_TASK_ID:-0}"
read -r LABEL CH0 CH1 <<< "${BANDS[$idx]}"

CAL=/scratch/$USER/paircars/out/fig4_raw/20151203/1133149192_target/calibrated_ms
MS0=$CAL/target_1133149192_ch_${CH0}_t_20151203033941_20151203034425.ms
MS1=$CAL/target_1133149192_ch_${CH1}_t_20151203033941_20151203034425.ms
OUT=/scratch/$USER/mwa/sharma2020/raw/casa_su_frames
CONCAT=/scratch/$USER/mwa/sharma2020/raw/concat/1133149192-ch${CH0}-${CH1}.ms
CODE="${PAPER_CODE:-$HOME/mwa/sharma2020}"
START="${START:-0}"
STOP="${STOP:-570}"

mkdir -p "$OUT" "$OUT/tmp-$LABEL" "$(dirname "$CONCAT")"
export TMPDIR="$OUT/tmp-$LABEL" TMP="$TMPDIR" TEMP="$TMPDIR"
export OPENBLAS_NUM_THREADS=1
cd "$OUT"

echo "node=$(hostname) label=$LABEL frames=${START}-${STOP}"
du -sh "$MS0" "$MS1"
python -c "import casatasks; print('casa-ok', casatasks.__file__)"

if [[ ! -d "$CONCAT" ]]; then
  python - <<PY
from casatasks import concat
concat(vis=["$MS0", "$MS1"], concatvis="$CONCAT", copypointing=False)
print("CONCAT_OK $CONCAT")
PY
fi
du -sh "$CONCAT"

python "$CODE/sharma2020_casa_snap.py" \
  "$CONCAT" "$OUT/${LABEL}MHz" \
  --all-frames --start "$START" --stop "$STOP"

echo "RAW_CASA_FRAMES_OK $LABEL"
