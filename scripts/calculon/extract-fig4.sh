#!/bin/bash
# Extract Figure 4 coarse channels (108, 162, 217, 240 MHz) from one ASVO tar.
#   bash extract-fig4.sh <obsid> <asvo_jobid>
set -euo pipefail
OBSID=${1:?obsid}
JOBID=${2:?asvo job id}
ARCHIVE=${ARCHIVE:-/mnt/nas05/data02/MWA_data/data/mwa_data2}
DEST=${DEST:-/scratch/$USER/mwa/sharma2020/raw/${OBSID}}
TAR="${ARCHIVE}/${OBSID}_${JOBID}_ms.tar"
CHANS=(084 085 125 126 169 170 187 188)

mkdir -p "$DEST"
cd "$DEST"
tar -tf "$TAR" > members.txt
mf=$(grep -E '\.metafits$' members.txt | head -1 || true)
if [[ -n $mf ]]; then
  tar -xf "$TAR" "$mf" || true
  find "$DEST" -name '*.metafits' -exec cp -n {} "$DEST/${OBSID}.metafits" \;
  [[ -f $DEST/${OBSID}.metafits ]] || cp -a "$(find "$DEST" -name '*.metafits' | head -1)" "$DEST/${OBSID}.metafits"
fi
for ch in "${CHANS[@]}"; do
  m=$(grep -E "ch0*${ch}([^0-9]|$)|[-_]0*${ch}[-_.]" members.txt \
      | sed 's#/.*##' | grep '\.ms$' | sort -u | head -1 || true)
  if [[ -z $m ]]; then
    echo "MISSING ${OBSID} ch${ch}" >&2
    continue
  fi
  echo "extract $m"
  tar -xf "$TAR" "$m"
  base=$(basename "$m")
  if [[ ! -e $DEST/$base ]]; then
    found=$(find "$DEST" -type d -name "$base" | head -1 || true)
    [[ -n $found && $found != "$DEST/$base" ]] && mv "$found" "$DEST/"
  fi
done
echo "EXTRACT_OK ${OBSID} $(find "$DEST" -maxdepth 1 -name '*.ms' | wc -l) MS"
ls -d "$DEST"/*.ms "$DEST"/*.metafits 2>/dev/null || true
