#!/usr/bin/env bash
# Apple Silicon install of P-AIRCARS: Colima (Rosetta) + Ubuntu linux/amd64.
#
#   scripts/paircars-mac/setup.sh
#   scripts/paircars-mac/setup.sh --skip-init    # container and Python only
#
# PAIRCAR_ROOT and PAIRCAR_DATA override the checkout and the data directory.
# Defaults sit next to this repository, under ~/Projects.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
PROJECTS="$(cd "$REPO/.." && pwd)"
ROOT="${PAIRCARS_ROOT:-$PROJECTS/P-AIRCARS}"
DATA="${PAIRCARS_DATA:-$PROJECTS/P-AIRCARS-data}"
PROFILE=paircars
CONTAINER=paircars
SKIP_INIT=0

usage() {
  echo "usage: $0 [--skip-init]" >&2
  exit 2
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-init) SKIP_INIT=1 ;;
    -h|--help) usage ;;
    *) usage ;;
  esac
  shift
done

if [[ "$(uname -s)" != "Darwin" || "$(uname -m)" != "arm64" ]]; then
  echo "This installer is for Apple Silicon Macs. P-AIRCARS itself is Linux x86_64." >&2
  exit 1
fi
command -v colima >/dev/null || { echo "Install Colima first: brew install colima docker" >&2; exit 1; }
command -v docker >/dev/null || { echo "Install Docker first: brew install colima docker" >&2; exit 1; }

if ! colima status --profile "$PROFILE" >/dev/null 2>&1; then
  colima start --profile "$PROFILE" \
    --vm-type vz --vz-rosetta \
    --cpu 8 --memory 16 --disk 100
fi

CTX=(docker --context "colima-$PROFILE")

if [[ ! -d "$ROOT/.git" ]]; then
  git clone --depth 1 https://github.com/devojyoti96/P-AIRCARS.git "$ROOT"
fi
mkdir -p "$DATA"/{meta,sample,work,out,target,cal,pipeline-work}

if ! "${CTX[@]}" inspect "$CONTAINER" >/dev/null 2>&1; then
  "${CTX[@]}" run -d --name "$CONTAINER" --platform linux/amd64 \
    -v "$ROOT:/opt/P-AIRCARS" \
    -v "$DATA:/data" \
    ubuntu:22.04 sleep infinity
fi
"${CTX[@]}" start "$CONTAINER" >/dev/null

"${CTX[@]}" cp "$HERE/macos_fixes.py" "$CONTAINER:/tmp/macos_fixes.py"
"${CTX[@]}" cp "$HERE/install-inside.sh" "$CONTAINER:/tmp/install-inside.sh"
"${CTX[@]}" exec -e SKIP_INIT="$SKIP_INIT" -e PAIRCARS_FIXES=/tmp/macos_fixes.py \
  "$CONTAINER" bash /tmp/install-inside.sh

echo
echo "Container:  $CONTAINER   (docker context colima-$PROFILE)"
echo "Checkout:   $ROOT"
echo "Data:       $DATA"
echo "Next:       scripts/paircars-mac/fetch-sample.sh"
echo "            scripts/paircars-mac/run-sample.sh"
