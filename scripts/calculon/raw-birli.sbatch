#!/bin/bash
# Raw MWAX visibilities of one coarse channel -> MS at the correlator time resolution.
# Stages (STAGES, space separated): extract (metafits + one channel's gpubox files
# from the ASVO tar), dryrun (birli --dry-run summary), convert (write the MS).
#   sbatch -M calc-cpu --export=ALL,STAGES="extract dryrun" ~/mwa/flare/raw-birli.sbatch
#   sbatch -M calc-cpu --export=ALL,STAGES=convert ~/mwa/flare/raw-birli.sbatch
# Birli options reviewed with André on 12 Oct 2026 (docs/asvo-request-1348547272.md):
# no AOFlagger (it flags solar bursts), native 0.25 s, 160 kHz, 80 kHz edge flags,
# metafits tile flags, default corrections, only the provided channel.
#SBATCH --job-name=raw-birli
#SBATCH --partition=cpu-daily
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=64G
#SBATCH --time=12:00:00
#SBATCH --output=logs/%x_%j.log

set -euo pipefail
source "$HOME/mwa/mwa-env.sh"
OBSID="${OBSID:-1348547272}"
CH="${CH:-116}"
TAR="${TAR:-/mnt/nas05/data02/MWA_data/data/mwa_data2/1348547272_1111033_vis.tar}"
W="${W:-/scratch/$USER/mwa/flare20220930_raw}"
STAGES="${STAGES:-extract dryrun}"
OUT="$W/${OBSID}_ch${CH}_0.25s.ms"
mkdir -p "$W"
cd "$W"

birli_run() {
  singularity exec --bind /scratch "$MWA_DEMO_SIF" birli \
    --metafits "$W/${OBSID}.metafits" \
    --provided-chan-ranges \
    --no-rfi \
    --flag-edge-width 80 \
    --avg-freq-res 160 \
    --max-memory 48 \
    --no-draw-progress \
    -M "$OUT" "$@" \
    "$W"/${OBSID}_*_ch${CH}_*.fits
}

for stage in $STAGES; do
  echo "== $(date -Is) stage $stage"
  case $stage in
    extract)
      tar -xvf "$TAR" --wildcards "*${OBSID}.metafits" "*_ch${CH}_*.fits" | tee "$W/extracted.txt"
      # files may sit in a sub-directory of the tar: move them up
      find "$W" -mindepth 2 \( -name "*.fits" -o -name "*.metafits" \) -exec mv {} "$W"/ \;
      ls -la "$W"
      ;;
    dryrun)
      birli_run --dry-run
      ;;
    convert)
      rm -rf "$OUT"
      birli_run
      du -sh "$OUT"
      ;;
  esac
done
echo "RAW_BIRLI_DONE $STAGES"
