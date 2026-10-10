#!/usr/bin/env bash
# Run the unpacked Zenodo sample inside the paircars container.
# fetch-sample.sh must have filled /data/target and /data/cal.
set -euo pipefail

PROFILE=paircars
CONTAINER=paircars

docker --context "colima-$PROFILE" exec \
  -u paircars \
  -e HOME=/home/paircars \
  -e USER=paircars \
  -e PYTHONUNBUFFERED=1 \
  -e PYTHONNOUSERSITE=1 \
  -e QT_QPA_PLATFORM=offscreen \
  -e MPLBACKEND=Agg \
  "$CONTAINER" bash -lc \
  'source /opt/miniforge3/etc/profile.d/conda.sh && conda activate paircars && \
   run-mwa-paircars /data/target \
     --cal_datadir /data/cal \
     --workdir /data/pipeline-work \
     --outdir /data/out \
     --max_worker 1 --cpu_frac 0.5 --mem_frac 0.6'

echo "Images land under \$PAIRCARS_DATA/out (default: the data directory next to this repo)."
echo "PNG contact sheet: scripts/paircars-mac/render_pngs.py"
