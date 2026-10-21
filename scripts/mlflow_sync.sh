#!/bin/bash
# Mirror the MLflow store of the archive-burst images from calculon to this Mac, so the
# MLflow UI runs locally (http://localhost:5050) without the VPN.
#   bash scripts/mlflow_sync.sh          # sync now (needs the VPN; quietly skips without it)
#   bash scripts/mlflow_sync.sh ui       # start the local UI if it is not running
# Local copy: ~/mwa-mlflow/{mlflow.db, artifacts/}; MLflow 3.17.1 in ~/mwa-mlflow/venv
# (same version as on calculon). Run every 30 min by the launchd agent ch.fhnw.mwa-mlflow-sync.
set -uo pipefail
L=$HOME/mwa-mlflow
R=/home2/andre_csillaghy/mwa/mlflow
PORT=${PORT:-5050}   # 5000 is taken by the macOS AirPlay receiver
mkdir -p "$L/artifacts"

ui() {
  if lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then return 0; fi
  MLFLOW_SERVER_ENABLE_JOB_EXECUTION=false MLFLOW_DISABLE_AGENT_HINT=1 \
    nohup "$L/venv/bin/mlflow" ui --host 127.0.0.1 --port "$PORT" --workers 1 \
    --backend-store-uri "sqlite:///$L/mlflow.db" > "$L/ui.log" 2>&1 < /dev/null &
  echo "MLflow UI on http://localhost:$PORT"
}

if [[ ${1:-} == ui ]]; then ui; exit 0; fi

# calculon only via the VPN: without it keep the copy, but make sure the UI runs
if ! ssh -o BatchMode=yes -o ConnectTimeout=8 calculon true 2>/dev/null; then
  echo "$(date '+%F %H:%M') no VPN, kept the copy of $(cat "$L/synced" 2>/dev/null || echo never)"
  ui; exit 0
fi

# consistent snapshot of the database on calculon (a run may be writing right now)
ssh -o BatchMode=yes calculon "$R/../mlflow-venv/bin/python -c \"import sqlite3; s=sqlite3.connect('$R/mlflow.db'); d=sqlite3.connect('$R/snapshot.db'); s.backup(d); d.close()\"" || exit 1
rsync -a --delete -e "ssh -o BatchMode=yes" "calculon:$R/artifacts/" "$L/artifacts/" || exit 1
rsync -a -e "ssh -o BatchMode=yes" "calculon:$R/snapshot.db" "$L/incoming.db" || exit 1

# artifact paths in the copy point to this Mac
"$L/venv/bin/python" - "$L" "$R" <<'EOF'
import sqlite3, sys
local, remote = sys.argv[1], sys.argv[2]
db = sqlite3.connect(f"{local}/incoming.db")
for table, col in (("runs", "artifact_uri"), ("experiments", "artifact_location")):
    db.execute(f"UPDATE {table} SET {col} = replace({col}, ?, ?)",
               (f"file://{remote}/artifacts", f"file://{local}/artifacts"))
db.commit()
db.close()
EOF
mv "$L/incoming.db" "$L/mlflow.db"
date '+%F %H:%M' > "$L/synced"
echo "$(date '+%F %H:%M') synced $(ls "$L/artifacts" | wc -l | tr -d ' ') run folders"
ui
