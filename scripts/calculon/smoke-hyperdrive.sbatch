#!/bin/bash
# André's hyperdrive vis-sim smoke test, on a calculon GPU node.
# Submit with scripts/calculon/submit-setup.sh (cluster `cluster`).
#SBATCH --job-name=mwa-smoke
#SBATCH --partition=debug
#SBATCH --gres=gpu:1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=16G
#SBATCH --time=00:30:00
#SBATCH --output=logs/%x-%j.out

set -euo pipefail
source "$HOME/mwa/mwa-env.sh"
mwa_mkdirs
cd "$MWA_SMOKE"

fetch() {
  local url="$1" dest="$2"
  if [[ -s "$dest" ]]; then
    echo "have $dest ($(du -h "$dest" | awk '{print $1}'))"
    return 0
  fi
  echo "GET $url"
  curl -fL --retry 3 --retry-delay 2 -o "$dest.partial" "$url"
  mv "$dest.partial" "$dest"
}

fetch 'https://ws.mwatelescope.org/metadata/fits?obs_id=1184702048' \
  "$MWA_SMOKE/1184702048.metafits"
fetch 'http://ws.mwatelescope.org/static/mwa_full_embedded_element_pattern.h5' \
  "$MWA_SMOKE/mwa_full_embedded_element_pattern.h5"
fetch 'https://github.com/GLEAM-X/GLEAM-X-pipeline/raw/master/models/GGSM_updated.fits' \
  "$MWA_SMOKE/GGSM_updated.fits"

echo "node=$(hostname) singularity=$(singularity --version)"
nvidia-smi -L
singularity exec --nv "$HYPERDRIVE_SIF" bash -lc \
  'command -v nvidia-smi; nvidia-smi -L; hyperdrive --version'

rm -f "$MWA_SMOKE/1184702048.uvfits"
singularity exec --nv "$HYPERDRIVE_SIF" bash -lc \
  "hyperdrive vis-sim \
    --beam-file='$MWA_SMOKE/mwa_full_embedded_element_pattern.h5' \
    --metafits='$MWA_SMOKE/1184702048.metafits' \
    --output-model-files='$MWA_SMOKE/1184702048.uvfits' \
    --source-list='$MWA_SMOKE/GGSM_updated.fits' \
    --num-sources=1"

ls -lh "$MWA_SMOKE/1184702048.uvfits"
echo SMOKE_DONE
