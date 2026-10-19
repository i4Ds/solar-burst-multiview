#!/bin/bash
# Extract every coarse-channel MS and the metafits of one ASVO obs into a
# P-AIRCARS data directory (/scratch/$USER/paircars/data/<obsid>_all).
#   sbatch -M calc-cpu --export=ALL,OBSID=1348547272 extract-all.sbatch
# TAR picks one tar when an obs has several (e.g. an old conversion with AOFlagger
# next to a new one); DEST overrides the target directory.
#SBATCH --job-name=extract-all
#SBATCH --partition=cpu-daily
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=03:00:00

set -euo pipefail
: "${OBSID:?set OBSID}"
archive="${ARCHIVE:-/mnt/nas05/data02/MWA_data/data/mwa_data}"
dest="${DEST:-/scratch/$USER/paircars/data/${OBSID}_all}"
tars=( "$archive"/${OBSID}_*_ms.tar )
tar="${TAR:-${tars[0]}}"
mkdir -p "$dest"
tar -xf "$tar" -C "$dest"
# files may sit in a sub-directory of the tar: move them up
find "$dest" -mindepth 2 -maxdepth 2 \( -name "*.ms" -o -name "*.metafits" \) -exec mv {} "$dest"/ \;
ls "$dest" | head -40
echo "$tar" > "$dest/EXTRACT_OK"
echo "EXTRACT_OK $OBSID $(ls -d "$dest"/*.ms | wc -l) MS"
