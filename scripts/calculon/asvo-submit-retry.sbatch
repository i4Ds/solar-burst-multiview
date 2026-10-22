#!/bin/bash
#SBATCH -M calc-cpu
#SBATCH -p cpu-daily
#SBATCH --time=23:50:00
#SBATCH -n1 -c1 --mem=1G
#SBATCH -J asvo-submit-retry
#SBATCH -o /home2/andre_csillaghy/mwa/logs/%x_%j.log
# Submit ASVO jobs one obsid at a time, retrying every 30 min only the obsids ASVO refused
# (outage, "status code 0"); an obsid that went through is never submitted again (23 Oct:
# the old version resubmitted the whole list after a partial failure).
# Env: OBSIDS (space separated), SUBMIT=conv|vis (default conv), PARAMS (conv only).
# Pass the values through the environment (VAR=... sbatch --export=ALL): sbatch --export
# splits at commas. Record the job ids from this log in configs/asvo_jobs.csv.
source ~/mwa/mwa-env.sh
export MWA_ASVO_API_KEY=$(<~/.config/mwa_asvo/api_key)
SUBMIT=${SUBMIT:-conv}
if [[ $SUBMIT == conv && $PARAMS != *no_rfi=true* ]]; then
  echo "PARAMS without no_rfi=true: AOFlagger stays off"; exit 2
fi
[[ $SUBMIT == conv || $SUBMIT == vis ]] || { echo "SUBMIT must be conv or vis"; exit 2; }
todo=($OBSIDS)
for i in $(seq 46); do
  left=()
  for o in "${todo[@]}"; do
    if [[ $SUBMIT == vis ]]; then out=$(singularity exec $MWA_DEMO_SIF giant-squid submit-vis "$o" 2>&1)
    else out=$(singularity exec $MWA_DEMO_SIF giant-squid submit-conv -p "$PARAMS" "$o" 2>&1); fi
    echo "$(date "+%F %T") attempt $i $o"; echo "$out" | grep -v -i api_key
    if echo "$out" | grep -q "status code 999"; then echo "REFUSED $o (embargo)"; continue; fi
    echo "$out" | grep -qiE "error|outage|status code" && left+=("$o")
  done
  [[ ${#left[@]} -eq 0 ]] && { echo SUBMIT_OK; exit 0; }
  todo=("${left[@]}"); echo "retry in 30 min: ${todo[*]}"; sleep 1800
done
echo "SUBMIT_GAVE_UP ${todo[*]}"; exit 1
