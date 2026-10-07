#!/bin/bash
# Extract every coarse-channel MS and the metafits of one ASVO obs into a
# P-AIRCARS data directory (/scratch/$USER/paircars/data/<obsid>_all).
#   sbatch -M calc-cpu --export=ALL,OBSID=1348547272 extract-all.sbatch
#SBATCH --job-name=extract-all
#SBATCH --partition=cpu-daily
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=03:00:00

set -euo pipefail
: "${OBSID:?set OBSID}"
archive="${ARCHIVE:-/mnt/nas05/data02/MWA_data/data/mwa_data}"
dest="/scratch/$USER/paircars/data/${OBSID}_all"
tars=( "$archive"/${OBSID}_*_ms.tar )
mkdir -p "$dest"
tar -xf "${tars[0]}" -C "$dest"
ls "$dest" | head -40
echo "EXTRACT_OK $OBSID $(ls -d "$dest"/*.ms | wc -l) MS"
