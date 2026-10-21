#!/bin/bash
# Run product_run.sh for a list of products, at most PAR at a time (P-AIRCARS shares one
# Prefect/Postgres server). One product per line, KEY=VALUE fields (no spaces in values):
#   SUN=1419137296 SUN_JOB=1114407 CAL=1419161128 CAL_JOB=1114408 DATEDIR=20241225 CH=127 \
#     LABEL=s1_045130_045200 TRES=1 TRANGE=2024/12/25/04:51:30~2024/12/25/04:52:00 REQUEST=<board request id>
# Products of the same observation and channel should not run at the same time (shared MS step).
#   setsid nohup bash ~/mwa/events/run_products.sh LIST > ~/mwa/products/logs/LIST.out 2>&1 < /dev/null &
# Stop a running list: kill its xargs first, then the product_run.sh processes.
LIST=$1
PAR=${PAR:-3}
SUMMARY=$HOME/mwa/products/logs/$(basename "$LIST" .txt).status
mkdir -p "$HOME/mwa/products/logs"
one() {
  local id
  id=$(env "$@" bash -c 'echo ${SUN}_ch${CH:-127}_${LABEL:-peak4s}')
  echo "$(date '+%F %H:%M') start $id" >> "$SUMMARY"
  env "$@" bash "$HOME/mwa/events/product_run.sh" > "$HOME/mwa/products/logs/$id.out" 2>&1
  echo "$(date '+%F %H:%M') end $id: $(grep -E '^- ' "$HOME/mwa/products/$id.md" | tail -n 1)" >> "$SUMMARY"
}
export -f one
export SUMMARY
echo "# $(basename "$LIST"), $PAR at a time, started $(date '+%F %H:%M')" > "$SUMMARY"
grep -v '^\s*#' "$LIST" | grep . | xargs -P "$PAR" -L 1 bash -c 'one "$@"' _
echo "$(date '+%F %H:%M') LIST_DONE" >> "$SUMMARY"
