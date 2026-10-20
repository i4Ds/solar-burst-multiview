#!/bin/bash
# MLflow web UI for the archive-burst images, on the calculon login node, localhost only.
#   ssh calculon 'bash ~/mwa/events/mlflow-ui.sh'        # start (once; stays up)
#   ssh -N -L 5000:localhost:5000 calculon               # on the Mac, then http://localhost:5000
#   ssh calculon 'bash ~/mwa/events/mlflow-ui.sh stop'
PORT=${PORT:-5000}
if [[ ${1:-} == stop ]]; then pkill -u "$USER" -f "mlflow ui.*--port $PORT" && echo stopped; exit 0; fi
if ss -ltn | grep -q "127.0.0.1:$PORT\b"; then echo "already running on localhost:$PORT"; exit 0; fi
# shared login node: one web worker, no background job runner (used only for GenAI evaluations)
MLFLOW_SERVER_ENABLE_JOB_EXECUTION=false \
setsid nohup ~/mwa/mlflow-venv/bin/mlflow ui --host 127.0.0.1 --port "$PORT" --workers 1 \
  --backend-store-uri "sqlite:///$HOME/mwa/mlflow/mlflow.db" \
  > ~/mwa/logs/mlflow-ui.log 2>&1 < /dev/null &
sleep 5; ss -ltn | grep -q "127.0.0.1:$PORT\b" && echo "MLflow UI on localhost:$PORT (tunnel: ssh -N -L $PORT:localhost:$PORT calculon)"
