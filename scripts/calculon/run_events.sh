#!/bin/bash
# Run event_image.sh for a list of events, at most PAR at a time (P-AIRCARS shares one
# Prefect/Postgres server). One line per event, whitespace separated:
#   SUN SUN_JOB CAL CAL_JOB DATEDIR [CH=nnn] LOGARGS...
# (CH defaults to 127; the calibrator must contain that coarse channel.)
# Stop a running batch by killing its xargs first, then the event_image.sh processes.
# Events that share a calibrator should not be next to each other in the list (the
# calibrator is extracted by the first one). Runs detached on the login node:
#   setsid nohup bash ~/mwa/events/run_events.sh ~/mwa/events/batch1.txt > ~/mwa/events/logs/batch1.out 2>&1 < /dev/null &
# Status per event: ~/mwa/events/<SUN>.md; summary: ~/mwa/events/logs/<list>.status
LIST=$1
PAR=${PAR:-3}
SUMMARY=$HOME/mwa/events/logs/$(basename "$LIST" .txt).status
one() {
  local sun=$1 sun_job=$2 cal=$3 cal_job=$4 datedir=$5 ch=127; shift 5
  # optional CH=nnn as 6th field: obs without channel 127 use the nearest channel
  if [[ ${1:-} == CH=* ]]; then ch=${1#CH=}; shift; fi
  echo "$(date '+%F %H:%M') start $sun ch$ch" >> "$SUMMARY"
  SUN=$sun SUN_JOB=$sun_job CAL=$cal CAL_JOB=$cal_job DATEDIR=$datedir CH=$ch LOGARGS="$*" \
    bash "$HOME/mwa/events/event_image.sh" > "$HOME/mwa/events/logs/$sun.out" 2>&1
  echo "$(date '+%F %H:%M') end $sun: $(tail -n 1 "$HOME/mwa/events/$sun.md")" >> "$SUMMARY"
}
export -f one
export SUMMARY
echo "# $(basename "$LIST"), $PAR at a time, started $(date '+%F %H:%M')" > "$SUMMARY"
grep -v '^\s*#' "$LIST" | grep . | xargs -P "$PAR" -L 1 bash -c 'one "$@"' _
echo "$(date '+%F %H:%M') BATCH_DONE" >> "$SUMMARY"
