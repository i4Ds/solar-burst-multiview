#!/bin/bash
#SBATCH -M calc-cpu
#SBATCH -p cpu-daily
#SBATCH --time=23:50:00
#SBATCH -n1 -c1 --mem=1G
#SBATCH -J asvo-watch
#SBATCH -o /home2/andre_csillaghy/mwa/logs/%x_%j.log
# Every 30 min: list the ASVO jobs and download each Ready one that is not yet on
# the NAS (asvo-download-retry.sbatch as job asvo-dl-<jobid>, at most MAXDL at once).
# Stops when nothing is pending; before its time limit it resubmits itself.
# Status: ~/mwa/asvo-watch.status. No Slurm mail (it never arrives on calculon).
#   sbatch ~/mwa/asvo-watch.sbatch
source ~/mwa/mwa-env.sh
export MWA_ASVO_API_KEY=$(<~/.config/mwa_asvo/api_key)
DEST=${DEST:-/mnt/nas05/data02/MWA_data/data/mwa_data2}
MAXDL=${MAXDL:-3}
STATUS=~/mwa/asvo-watch.status
RUN=$(mktemp)
stop=$((SECONDS + 23 * 3600))
cd ~/mwa
while (( SECONDS < stop )); do
  squeue -M calc-cpu -u "$USER" -h -o %j > "$RUN"
  json=$(singularity exec "$MWA_DEMO_SIF" giant-squid list --json 2>&1)
  out=$(python3 ~/mwa/asvo_watch.py "$DEST" "$MAXDL" "$RUN" "$STATUS" <<<"$json")
  echo "$(date -Is)"; cat "$STATUS"
  while read -r tag jobid obsid kind bytes; do
    [[ $tag == DL ]] || continue
    sbatch -M calc-cpu -J "asvo-dl-$jobid" \
      --export=ALL,JOBID=$jobid,OBSID=$obsid,KIND=$kind,BYTES=$bytes,DEST=$DEST ~/mwa/asvo-download-retry.sbatch
  done <<<"$out"
  if grep -q '^PENDING 0$' <<<"$out"; then echo "$(date -Is) ASVO_WATCH_DONE"; rm -f "$RUN"; exit 0; fi
  sleep 1800
done
rm -f "$RUN"
echo "$(date -Is) time limit: resubmitting"
sbatch ~/mwa/asvo-watch.sbatch
