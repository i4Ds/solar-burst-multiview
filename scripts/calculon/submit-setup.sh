#!/bin/bash
# Run this on the calculon login node. It installs ~/mwa/mwa-env.sh and
# submits the image pull (CPU cluster) and the hyperdrive smoke test (GPU
# cluster). Cross-cluster job dependencies are not used; the smoke test is
# submitted with --dependency only when both jobs share a scheduler. Pass
# --pull-only or --smoke-only to submit one side.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$HOME/mwa/logs"
cp "$HERE/mwa-env.sh" "$HOME/mwa/mwa-env.sh"
# shellcheck disable=SC1091
source "$HOME/mwa/mwa-env.sh"
mwa_mkdirs

mode="${1:-all}"
cd "$HOME/mwa"

submit_pull() {
  sbatch --parsable --cluster=calc-cpu "$HERE/pull-images.sbatch"
}

submit_smoke() {
  sbatch --parsable --cluster=cluster "$HERE/smoke-hyperdrive.sbatch"
}

case "$mode" in
  all)
    pull_id="$(submit_pull)"
    echo "pull job ${pull_id}"
    echo "smoke test is separate: after the pull finishes, rerun with --smoke-only"
    ;;
  --pull-only) echo "pull job $(submit_pull)" ;;
  --smoke-only) echo "smoke job $(submit_smoke)" ;;
  *)
    echo "usage: $0 [--pull-only|--smoke-only]" >&2
    exit 2
    ;;
esac

squeue --cluster=calc-cpu -u "$USER" || true
squeue --cluster=cluster -u "$USER" || true
