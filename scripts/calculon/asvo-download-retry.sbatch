#!/bin/bash
# Download one MWA ASVO job (acacia tar) to the calculon NAS, resuming after
# network errors until the tar has the expected size.
# giant-squid exits 0 even after "[ERROR] request or response body error", so
# the plain download job ends early; this one checks the log and the size.
#   sbatch -M calc-cpu --export=ALL,JOBID=1111033,OBSID=1348547272,KIND=vis,BYTES=1088774161920 \
#     ~/mwa/asvo-download-retry.sbatch
# The API key is read from ~/.config/mwa_asvo/api_key (mode 600), never put on a command line.
#SBATCH --job-name=asvo-dl-retry
#SBATCH --partition=cpu-daily
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=23:59:00
#SBATCH --output=logs/%x-%j.out

set -uo pipefail
source "$HOME/mwa/mwa-env.sh"
: "${JOBID:?set JOBID}" "${OBSID:?set OBSID}" "${BYTES:?set BYTES (expected data size)}"
KIND="${KIND:-vis}"
DEST="${DEST:-/mnt/nas05/data02/MWA_data/data/mwa_data2}"
TAR="$DEST/${OBSID}_${JOBID}_${KIND}.tar"
MAX="${MAX:-30}"
export MWA_ASVO_API_KEY="$(<"$HOME/.config/mwa_asvo/api_key")"
gs() { singularity exec -B /mnt/nas05/data02 "$MWA_DEMO_SIF" giant-squid "$@"; }

for i in $(seq 1 "$MAX"); do
  size=$(stat -c %s "$TAR" 2>/dev/null || echo 0)
  echo "$(date -Is) attempt $i, $TAR has $size bytes (data $BYTES)"
  out=$(gs download --keep-tar -d "$DEST" "$JOBID" 2>&1); echo "$out" | tail -3
  if ! grep -q "\[ERROR\]" <<<"$out" && [[ $(stat -c %s "$TAR" 2>/dev/null || echo 0) -ge $BYTES ]]; then
    echo "$(date -Is) DOWNLOAD_OK $(stat -c %s "$TAR") bytes"; ls -lh "$TAR"; exit 0
  fi
  sleep 60
done
echo "$(date -Is) DOWNLOAD_INCOMPLETE after $MAX attempts"; exit 1
