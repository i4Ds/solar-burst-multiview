#!/bin/bash
# Bring the MWA image board on the laptop up to date (needs the VPN; skips quietly without).
#   bash ~/mwa-board/bin/sync_board.sh
# 1. copy the export from calculon (~/mwa/board: board.json, data, img, movies);
#    the laptop's own files stay: judgements.json, requests.json, bin/, e-Callisto spectra
# 2. e-Callisto dynamic spectra for new events (board_spectra.py, conda env with ecallisto_ng)
# 3. the page as pure ASCII from the template (asciify.py)
# Installed in ~/mwa-board/bin with serve_board.py; run every 30 min by the launchd agent
# ch.fhnw.mwa-board-sync, the server by ch.fhnw.mwa-board-server (http://localhost:8793).
set -uo pipefail
B=$HOME/mwa-board
BIN=$B/bin
PY=${PY:-$HOME/miniforge3/envs/solar-burst-multiview/bin/python}
if ! ssh -o BatchMode=yes -o ConnectTimeout=8 calculon true 2>/dev/null; then
  echo "$(date '+%F %H:%M') no VPN, board kept as of $(cat "$B/synced" 2>/dev/null || echo never)"; exit 0
fi
rsync -a --delete -e "ssh -o BatchMode=yes" \
  --exclude judgements.json --exclude requests.json --exclude bin/ --exclude index.html --exclude synced \
  --exclude 'img/*_spectrum.png' --exclude '*.stamp' --exclude '*.log' \
  calculon:mwa/board/ "$B/" || exit 1
(cd "$BIN" && "$PY" board_spectra.py "$B/board.json" --outdir "$B/img" 2>&1 | grep -v -i warn)
"$PY" "$BIN/asciify.py" "$BIN/index.html" "$B/index.html"
date '+%F %H:%M' > "$B/synced"
echo "$(date '+%F %H:%M') synced: $(ls "$B/data" 2>/dev/null | wc -l | tr -d ' ') image files, $(ls "$B/movies"/*.mp4 2>/dev/null | wc -l | tr -d ' ') movies"
