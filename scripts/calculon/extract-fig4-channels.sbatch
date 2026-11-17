#!/bin/bash
# Extract the eight Figure 4 coarse channels (108, 162, 217, 240 MHz) and
# the metafits from one ASVO conversion tar. Does not touch Rohit's tree.
#   sbatch -M calc-cpu --export=ALL,OBSID=1133149192,JOBID=<id> \
#     scripts/calculon/extract-fig4-channels.sbatch
#SBATCH --job-name=extract-fig4
#SBATCH --partition=cpu-daily
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=03:00:00
#SBATCH --output=/home2/andre_csillaghy/mwa/logs/%x_%j.log

set -euo pipefail
: "${OBSID:?set OBSID}"
: "${JOBID:?set JOBID}"
ARCHIVE="${ARCHIVE:-/mnt/nas05/data02/MWA_data/data/mwa_data2}"
DEST="${DEST:-/scratch/$USER/mwa/sharma2020/raw/${OBSID}}"
TAR="${ARCHIVE}/${OBSID}_${JOBID}_ms.tar"
# Figure 4: 108, 162, 217, 240 MHz
CHANS=(084 085 125 126 169 170 187 188)

mkdir -p "$DEST"
cd "$DEST"
tar -tf "$TAR" > members.txt
tar -xf "$TAR" --wildcards --no-anchored "${OBSID}.metafits" "*.metafits" || true
for ch in "${CHANS[@]}"; do
  m=$(grep -E "ch0*${ch}([^0-9]|$)|[-_]0*${ch}[-_.]" members.txt | grep -E '\.ms/?$' | head -1 || true)
  if [ -z "$m" ]; then
    echo "MISSING ch${ch}" >&2
    continue
  fi
  echo "extract $m"
  tar -xf "$TAR" "$m"
done
echo "EXTRACT_OK $OBSID $(find "$DEST" -name '*.ms' -o -name '*.ms/' | wc -l) MS"
