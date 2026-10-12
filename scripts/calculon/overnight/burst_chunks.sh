#!/bin/bash
# A long P-AIRCARS image series in time chunks, one after the other, with
# burst_series.sh. All chunks share one TAG, so calibration and self-cal from the
# first chunk are reused and the whole series is calibrated the same way.
# Stops at the first chunk without images. Runs detached on the login node:
#   setsid nohup bash ~/overnight/bin/burst_chunks.sh > ~/overnight/<TAG>_chunks.log 2>&1 < /dev/null &
# Environment: as burst_series.sh (SRC_MS, METAFITS, TAG, TRES, ...), plus
#   CHUNKS  "LABEL=HH:MM:SS~HH:MM:SS ..." on 2022/09/30
# Default: the whole 0.25 s ch116 observation, main burst first (P-AIRCARS accepts
# 04:27:41-04:32:23 only).
set -uo pipefail
export SRC_MS=${SRC_MS:-/scratch/$USER/mwa/flare20220930_raw/1348547272_ch116_0.25s.ms}
export METAFITS=${METAFITS:-/scratch/$USER/mwa/flare20220930_raw/1348547272.metafits}
export TAG=${TAG:-1348547272_025s_ch116}
export TRES=${TRES:-0.25}
export MEMFRAC=${MEMFRAC:-0.10} WALL=${WALL:-12:00:00}
CHUNKS=${CHUNKS:-"c2_burst=04:28:16~04:29:12 c1_pre=04:27:41~04:28:16 c3=04:29:12~04:30:08 c4=04:30:08~04:31:04 c5=04:31:04~04:32:23"}
P=/scratch/$USER/paircars
for c in $CHUNKS; do
  export LABEL=${c%%=*} r=${c#*=}
  export TRANGE="2022/09/30/${r%~*}~2022/09/30/${r#*~}"
  echo "$(date '+%F %T') chunk $LABEL $TRANGE"
  bash "$HOME/overnight/bin/burst_series.sh"
  n=$(ls "$P"/out/$TAG/20220930/*_target/imagedir_*_$LABEL/pbcor_hpcs/*.fits 2>/dev/null | wc -l)
  echo "$(date '+%F %T') chunk $LABEL: $n images"
  [[ $n -gt 0 ]] || { echo "stopping: chunk $LABEL has no images"; exit 1; }
done
echo "$(date '+%F %T') all chunks done"
