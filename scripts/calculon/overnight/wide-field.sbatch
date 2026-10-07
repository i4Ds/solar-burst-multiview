#!/bin/bash
# Wide-field wsclean image of one calibrated MS, for checking positions against GLEAM/GGSM.
# Optionally applies hyperdrive solutions first (SOLUTIONS + METAFITS).
#   sbatch --export=ALL,MS=...,NAME=...,DATACOL=DATA[,SOLUTIONS=...,METAFITS=...][,MULTISCALE=1][,MINUV=150] wide-field.sbatch
# Defaults: 5120 px x 25" (35.6 deg), all time steps, Briggs 0, auto-masked clean.
#SBATCH --job-name=wide-field
#SBATCH --partition=p3080
#SBATCH --gres=gpu:rtx3080:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=24G
#SBATCH --time=04:00:00

set -euo pipefail
source "$HOME/mwa/mwa-env.sh"
: "${MS:?set MS}" "${NAME:?set NAME}"
DATACOL="${DATACOL:-DATA}"
SIZE="${SIZE:-5120}"
SCALE="${SCALE:-25asec}"
out="${OUTDIR:-/scratch/$USER/overnight/img}"
mkdir -p "$out"
run() { singularity exec --nv --bind /scratch "$MWA_DEMO_SIF" "$@"; }

ms="$MS"
if [[ -n ${SOLUTIONS:-} ]]; then
  cal="${MS%.ms}_cal.ms"
  if [[ ! -d $cal ]]; then
    run hyperdrive solutions-apply --data "$MS" "${METAFITS:?set METAFITS}" \
      --solutions "$SOLUTIONS" --outputs "$cal"
  fi
  ms="$cal"
fi

extra=()
[[ ${MULTISCALE:-0} == 1 ]] && extra+=(-multiscale)
[[ -n ${MINUV:-} ]] && extra+=(-minuv-l "$MINUV")
echo "node=$(hostname) ms=$ms datacol=$DATACOL size=$SIZE scale=$SCALE ${extra[*]}"
run wsclean -name "$out/$NAME" -data-column "$DATACOL" \
  -size "$SIZE" "$SIZE" -scale "$SCALE" -pol I -weight briggs 0 \
  -niter 50000 -mgain 0.8 -auto-threshold 3 -auto-mask 5 -no-update-model-required "${extra[@]}" \
  -j "${SLURM_CPUS_PER_TASK}" "$ms"
ls -lh "$out/$NAME"-image.fits
echo "WIDE_OK $NAME"
