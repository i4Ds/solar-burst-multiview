#!/bin/bash
# Solve one Pictor A coarse channel on a calculon GPU node.
# Submit from ~/mwa (GPU cluster is the default; do not pass -M):
#   sbatch --export=ALL,CAL_OBSID=...,CHANNEL=... ~/mwa/cal/di-calibrate.sbatch
# Required environment: CAL_OBSID, CHANNEL.
# https://fhnw-hpc.pages.fhnw.ch/docs/runjobs/
# One RTX 3080. General partitions allow about 3–3.5 GB per core.
#SBATCH --job-name=mwa-dical
#SBATCH --partition=p3080
#SBATCH --gres=gpu:rtx3080:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=24G
#SBATCH --time=04:00:00
#SBATCH --output=logs/%x_%j.log

set -euo pipefail
source "$HOME/mwa/mwa-env.sh"

: "${CAL_OBSID:?set CAL_OBSID}"
: "${CHANNEL:?set CHANNEL}"

root="/scratch/${USER}/mwa/cal/${CAL_OBSID}"
ms="$root/${CAL_OBSID}_ch${CHANNEL}.ms"
meta="$root/${CAL_OBSID}.metafits"
src="$HOME/mwa/cal/GGSM_updated.fits"
beam="$HOME/mwa/smoke/mwa_full_embedded_element_pattern.h5"
out="$root/cal/hyp_soln_ch${CHANNEL}.fits"
partial="${out}.partial"

mkdir -p "$root/cal"
rm -f "$partial"

echo "node=$(hostname) obsid=${CAL_OBSID} channel=${CHANNEL}"
echo "ms=${ms}"
echo "source-list=${src}"
nvidia-smi -L

# Hyperdrive's OpenBLAS build must stay single-threaded. Other threads follow the allocation.
export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK}"
export OPENBLAS_NUM_THREADS=1

singularity exec --nv "$MWA_DEMO_SIF" bash -lc \
  "export OMP_NUM_THREADS=$(printf %q "$OMP_NUM_THREADS"); export OPENBLAS_NUM_THREADS=1; export MWA_BEAM_FILE=$(printf %q "$beam"); \
   hyperdrive di-calibrate \
     --tile-flags HexE21 HexE22 HexE23 HexE24 LBA1 \
     --source-list $(printf %q "$src") \
     --data $(printf %q "$ms") $(printf %q "$meta") \
     --outputs $(printf %q "$partial")"

test -s "$partial"
mv "$partial" "$out"
ls -lh "$out"
echo DICAL_DONE
