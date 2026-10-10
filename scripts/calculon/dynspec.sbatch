#!/bin/bash
# MWA dynamic spectrum over several observations, on the CPU cluster.
# Each obs tarball is extracted inside the job (never on the login node), reduced
# to short-baseline amplitudes by solarburst.dynspec, then deleted.
# Submit from ~/mwa:
#   sbatch -M calc-cpu --export=ALL,OBSIDS="1348544016 1348544312 ...",TAG=flare20220930 \
#     ~/mwa/flare/dynspec.sbatch
# As an array, one obs per task and one npz each (merge with dynspec.py OUT.npz *.npz):
#   sbatch -M calc-cpu --array=0-16%6 --export=ALL,OBSIDS="...",TAG=... ~/mwa/flare/dynspec.sbatch
#SBATCH --job-name=mwa-dynspec
#SBATCH --partition=cpu-daily
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=12G
#SBATCH --time=06:00:00
#SBATCH --output=logs/%x_%A_%a.log

set -euo pipefail
source "$HOME/mwa/mwa-env.sh"

: "${OBSIDS:?set OBSIDS}"
TAG="${TAG:-dynspec}"
archive="${ARCHIVE:-/mnt/nas05/data02/MWA_data/data/mwa_data}"
dynspec="${DYNSPEC_PY:-$HOME/mwa/flare/dynspec.py}"   # copy of src/solarburst/dynspec.py
root="/scratch/${USER}/mwa/${TAG}"
out="$root/dynspec_${TAG}.npz"
read -ra obslist <<< "$OBSIDS"
if [[ -n ${SLURM_ARRAY_TASK_ID:-} ]]; then
  obslist=( "${obslist[$SLURM_ARRAY_TASK_ID]}" )
  out="$root/dynspec_${TAG}_${obslist[0]}.npz"
fi
mkdir -p "$root/tmp"

for obs in "${obslist[@]}"; do
  tars=( "$archive"/${obs}_*_ms.tar )
  if [[ ! -e ${tars[0]} ]]; then
    echo "MISSING ${obs}"
    continue
  fi
  work="$root/tmp/$obs"
  rm -rf "$work"; mkdir -p "$work"
  tar -xf "${tars[0]}" -C "$work"
  singularity exec --bind /scratch "$MWA_DEMO_SIF" python3 "$dynspec" "$out" "$work"/${obs}_ch*.ms
  rm -rf "$work"
  echo "DONE ${obs}"
done
ls -lh "$out"
echo DYNSPEC_DONE
