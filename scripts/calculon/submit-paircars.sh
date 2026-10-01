#!/bin/bash
# Run on the calculon login node. Installs ~/paircars/env.sh and submits
# init on cluster calc-cpu. The conda env must already exist at
# ~/paircars/miniforge3/envs/paircars (paircars 3.0.6, Python 3.10).
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$HOME/paircars" /scratch/"$USER"/paircars/logs
cp "$HERE/paircars-env.sh" "$HOME/paircars/env.sh"
# shellcheck disable=SC1091
source "$HOME/paircars/env.sh"

mode="${1:-init}"
case "$mode" in
  init)
    jid=$(sbatch --parsable --cluster=calc-cpu "$HERE/paircars-init.sbatch")
    echo "init job ${jid}"
    ;;
  *)
    echo "usage: $0 [init]" >&2
    exit 2
    ;;
esac

squeue --cluster=calc-cpu -u "$USER" || true
