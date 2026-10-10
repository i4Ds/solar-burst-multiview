#!/usr/bin/env bash
# Download and unpack the P-AIRCARS Zenodo sample (record 18641232).
# Solar OBSID 1111474560 and calibrator 1111476056, three coarse-channel pairs each.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
DATA="${PAIRCARS_DATA:-$(cd "$REPO/.." && pwd)/P-AIRCARS-data}"
SAMPLE="$DATA/sample"
BASE="https://zenodo.org/records/18641232/files"

mkdir -p "$SAMPLE" "$DATA/target" "$DATA/cal"

fetch() {
  local name="$1" expect_size="$2" expect_md5="$3"
  local dest="$SAMPLE/$name"
  if [[ -f "$dest" ]] && [[ "$(md5 -q "$dest")" == "$expect_md5" ]]; then
    echo "$name already verified"
    return
  fi
  echo "downloading $name"
  curl -fL --retry 5 --retry-all-errors -C - -o "$dest.part" "$BASE/$name?download=1"
  mv "$dest.part" "$dest"
  local size md5sum
  size="$(stat -f %z "$dest")"
  md5sum="$(md5 -q "$dest")"
  if [[ "$size" != "$expect_size" || "$md5sum" != "$expect_md5" ]]; then
    echo "$name failed checksum: size=$size md5=$md5sum" >&2
    exit 1
  fi
  echo "$name md5=$md5sum OK"
}

fetch 1111474560.tar.gz 375174986 b51b6f91b77f55a3f39eaef24fcc5a1f
fetch 1111476056.tar.gz 229578191 199524f180b90c526dffeeb83d9bdaf0

rm -rf "$DATA/target"/* "$DATA/cal"/*
tar -xzf "$SAMPLE/1111474560.tar.gz" -C "$DATA/target"
tar -xzf "$SAMPLE/1111476056.tar.gz" -C "$DATA/cal"
echo "solar:      $DATA/target"
echo "calibrator: $DATA/cal"
