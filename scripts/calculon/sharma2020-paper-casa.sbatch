#!/bin/bash
# One CASA 0.5 s snapshot per Fig. 4 band, Sharma & Oberoi 2020 imaging
# parameters. Queued behind the WSClean comparison array so the two do not
# lock the same MS. Writes only under /scratch/$USER/mwa/sharma2020/paper/.
#
#   sbatch -M calc-cpu --dependency=afterany:168583 \
#     ~/mwa/sharma2020/sharma2020-paper-casa.sbatch
#   # more snapshots later:
#   sbatch -M calc-cpu --export=ALL,N_SNAP=10 ~/mwa/sharma2020/sharma2020-paper-casa.sbatch
#
#SBATCH --job-name=so2020-casa
#SBATCH --partition=cpu-daily
#SBATCH --time=08:00:00
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
# SuperUniform / niter 8000, not the earlier Briggs/2500 remake in paper/casa.
OUT=/scratch/$USER/mwa/sharma2020/paper/casa_su
CODE="${PAPER_CODE:-$HOME/mwa/sharma2020}"
N_SNAP="${N_SNAP:-1}"
mkdir -p "$OUT" "$HOME/mwa/logs" "$OUT/tmp-$LABEL"

export TMPDIR="$OUT/tmp-$LABEL"
export TMP="$TMPDIR"
export TEMP="$TMPDIR"
export OPENBLAS_NUM_THREADS=1
cd "$OUT"

echo "node=$(hostname) label=$LABEL n_snap=$N_SNAP ms=$MS"
du -sh "$MS"
python -c "import casatasks,casacore; print('casa-ok', casatasks.__file__)"

python "$CODE/sharma2020_casa_snap.py" \
  "$MS" "$OUT/${LABEL}MHz"

echo "PAPER_CASA_OK $LABEL"
