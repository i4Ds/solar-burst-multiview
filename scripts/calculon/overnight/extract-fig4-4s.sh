#!/bin/bash
# Extract Figure 4 coarse-channel pairs from the October 4 s ASVO tars.
#   bash extract-fig4-4s.sh
set -euo pipefail
DL=/mnt/nas05/data02/MWA_data/data/mwa_data2
W=/scratch/$USER/mwa/quiet2015
PAIRS=(84-85 125-126 169-170 187-188)
for spec in 1133149192:1113526 1133161488:1113527; do
  o=${spec%%:*}; job=${spec##*:}
  tar="$DL/${o}_${job}_ms.tar"
  dest="$W/$o"
  mkdir -p "$dest"
  cd "$dest"
  if [[ ! -f $dest/${o}.metafits ]]; then
    tar -xf "$tar" "./${o}.metafits" 2>/dev/null || tar -xf "$tar" "${o}.metafits"
  fi
  for pair in "${PAIRS[@]}"; do
    ms=${o}_ch${pair}.ms
    if [[ -d $dest/$ms ]]; then
      echo "skip $ms"
      continue
    fi
    echo "extract $ms"
    tar -xf "$tar" "./$ms" 2>/dev/null || tar -xf "$tar" "$ms"
  done
done
echo EXTRACT_OK
ls -d "$W"/1133149192/*.ms "$W"/1133161488/*.ms
