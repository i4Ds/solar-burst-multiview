#!/bin/bash
# Extract Figure 4 coarse-channel pairs from one ASVO tar.
# Names in the tar are e.g. 1133149192_ch84-85.ms (not ch084).
#   bash extract-fig4.sh <obsid> <asvo_jobid>
set -euo pipefail
OBSID=${1:?obsid}
JOBID=${2:?asvo job id}
ARCHIVE=${ARCHIVE:-/mnt/nas05/data02/MWA_data/data/mwa_data2}
DEST=${DEST:-/scratch/$USER/mwa/sharma2020/raw/${OBSID}}
TAR="${ARCHIVE}/${OBSID}_${JOBID}_ms.tar"
# 108, 162, 217, 240 MHz
PAIRS=(84-85 125-126 169-170 187-188)

mkdir -p "$DEST"
cd "$DEST"
[[ -f members.txt ]] || tar -tf "$TAR" > members.txt
mf=$(grep -E '\.metafits$' members.txt | head -1 || true)
if [[ -n $mf ]]; then
  tar -xf "$TAR" "$mf" || true
  got=$(find "$DEST" -name '*.metafits' | head -1 || true)
  [[ -n $got ]] && cp -n "$got" "$DEST/${OBSID}.metafits" 2>/dev/null || cp -a "$got" "$DEST/${OBSID}.metafits"
fi
n=0
for pair in "${PAIRS[@]}"; do
  m=$(grep -E "/?${OBSID}_ch${pair}\\.ms/?$" members.txt | head -1 || true)
  [[ -n $m ]] || m=$(grep "ch${pair}.ms" members.txt | sed 's#/.*##' | sort -u | head -1 || true)
  if [[ -z $m ]]; then
    echo "MISSING ${OBSID} ch${pair}" >&2
    continue
  fi
  m=${m#./}
  echo "extract $m"
  tar -xf "$TAR" "./$m" 2>/dev/null || tar -xf "$TAR" "$m"
  n=$((n + 1))
done
echo "EXTRACT_OK ${OBSID} ${n} MS"
ls -d "$DEST"/*.ms "$DEST"/*.metafits 2>/dev/null || true
[[ $n -eq 4 ]]
