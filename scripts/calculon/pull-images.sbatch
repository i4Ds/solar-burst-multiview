#!/bin/bash
# Pull the MWA images on a CPU node (Apptainer). Submit from calculon with
# scripts/calculon/submit-setup.sh, which selects cluster calc-cpu.
#SBATCH --job-name=mwa-pull
#SBATCH --partition=cpu-daily
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=06:00:00
#SBATCH --output=logs/%x-%j.out

set -euo pipefail
source "$HOME/mwa/mwa-env.sh"
mwa_mkdirs
cd "$MWA_IMAGES"

pull() {
  local dest="$1" uri="$2"
  if [[ -f "$dest" ]] && singularity exec "$dest" true; then
    echo "already present: $dest"
    return 0
  fi
  rm -f "$dest"
  echo "PULL $uri"
  singularity pull "$dest" "$uri"
  ls -lh "$dest"
}

inventory() {
  local name="$1" sif="$2"
  echo "===== $name ====="
  singularity exec "$sif" bash -lc '
    for c in hyperdrive birli wsclean giant-squid aoflagger DP3 dp3 chips ssins python3; do
      if command -v "$c" >/dev/null 2>&1; then
        printf "OK %s -> %s\n" "$c" "$(command -v "$c")"
      else
        echo "MISSING $c"
      fi
    done
    echo "-- versions --"
    hyperdrive --version 2>&1 | head -3 || true
    wsclean --version 2>&1 | head -3 || true
    birli --version 2>&1 | head -3 || true
  '
}

echo "node=$(hostname) singularity=$(singularity --version)"
pull "$HYPERDRIVE_SIF" "$HYPERDRIVE_URI"
pull "$MWA_DEMO_SIF" "$MWA_DEMO_URI"

set +e
pull "$SWISS_SIF" "$SWISS_URI"
swiss_rc=$?
set -e
echo "swiss_rc=$swiss_rc"

inventory hyperdrive "$HYPERDRIVE_SIF"
inventory mwa-demo "$MWA_DEMO_SIF"
if [[ "$swiss_rc" -eq 0 && -f "$SWISS_SIF" ]]; then
  inventory swiss "$SWISS_SIF"
fi
echo PULL_DONE
