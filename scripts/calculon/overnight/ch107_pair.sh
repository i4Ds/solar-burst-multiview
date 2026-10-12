#!/bin/bash
# Quiet-Sun and burst images on the same coarse channel, ch107 (137.0 MHz), the
# nearest channel common to the old (before 04:27:34) and new channel lists.
# Both runs use 3C444 (1348574416) as calibrator, so they differ only in time.
#   quiet: 1348546680, 04:17:44-04:22:36, 4 s archive data, one long integration
#   burst: 1348547272, 2 s data, 04:28:20-04:29:10 at 2 s (as the ch116 series)
# Runs detached on the login node:
#   setsid nohup bash ~/overnight/bin/ch107_pair.sh > ~/overnight/ch107_pair.log 2>&1 < /dev/null &
set -uo pipefail
M=/scratch/$USER/mwa
Q=$M/flare20220930_quiet
B=$M/flare20220930_025s
BIN=$HOME/overnight/bin
S=/scratch/$USER/overnight
mkdir -p "$S/logs"

# --- extract ch107 from both archive tarballs (CPU job; no big tar on the login node)
if [[ ! -d $Q/1348546680_ch107.ms || ! -d $B/1348547272_ch107.ms ]]; then
  j=$(sbatch -M calc-cpu -p cpu-daily --time=02:00:00 -n1 -c2 --mem=4G -J extract-ch107 -o "$S/logs/%x_%j.log" \
      --wrap "set -e; mkdir -p $Q $B; \
        tar -xf /mnt/nas05/data02/MWA_data/data/mwa_data/1348546680_867319_ms.tar -C $Q ./1348546680_ch107.ms ./1348546680.metafits; \
        tar -xf /mnt/nas05/data02/MWA_data/data/mwa_data2/1348547272_1109734_ms.tar -C $B ./1348547272_ch107.ms; \
        echo EXTRACT_OK" | awk '{print $4}')
  echo "extract job $j"
  while squeue -M calc-cpu -h -j "$j" 2>/dev/null | grep -q .; do sleep 60; done
fi
[[ -d $Q/1348546680_ch107.ms && -d $B/1348547272_ch107.ms ]] || { echo "extraction failed"; exit 1; }

# --- quiet Sun: one image over the quiet observation
SUN=1348546680 SRC_MS=$Q/1348546680_ch107.ms METAFITS=$Q/1348546680.metafits TAG=1348546680_ch107 \
  TRANGE="2022/09/30/04:18:00~2022/09/30/04:22:20" TRES=260 LABEL=quiet \
  bash "$BIN/burst_series.sh"

# --- burst at the same channel and calibrator
SUN=1348547272 SRC_MS=$B/1348547272_ch107.ms METAFITS=$B/1348547272.metafits TAG=1348547272_2s_ch107 \
  TRANGE="2022/09/30/04:28:20~2022/09/30/04:29:10" TRES=2 LABEL=burst \
  bash "$BIN/burst_series.sh"
