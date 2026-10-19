#!/bin/bash
#SBATCH -M calc-cpu
#SBATCH -p cpu-daily
#SBATCH --time=23:50:00
#SBATCH -n1 -c1 --mem=1G
#SBATCH -J asvo-submit-retry
#SBATCH -o /home2/andre_csillaghy/mwa/logs/%x_%j.log
# Submit ASVO jobs, retrying every 30 min while ASVO refuses (e.g. outage).
# Env: OBSIDS (space separated), SUBMIT=conv|vis (default conv), PARAMS (conv only).
# Lines are written by `python -m solarburst.obsstore plan`; record the job ids
# from this log in configs/asvo_jobs.csv. Conversions always carry no_rfi=true.
source ~/mwa/mwa-env.sh
export MWA_ASVO_API_KEY=$(<~/.config/mwa_asvo/api_key)
SUBMIT=${SUBMIT:-conv}
case $SUBMIT in
  vis) cmd=(giant-squid submit-vis $OBSIDS) ;;
  conv)
    [[ $PARAMS == *no_rfi=true* ]] || { echo "PARAMS without no_rfi=true: AOFlagger stays off"; exit 2; }
    cmd=(giant-squid submit-conv -p "$PARAMS" $OBSIDS) ;;
  *) echo "SUBMIT must be conv or vis"; exit 2 ;;
esac
for i in $(seq 46); do
  out=$(singularity exec $MWA_DEMO_SIF "${cmd[@]}" 2>&1)
  echo "$(date "+%F %T") attempt $i"; echo "$out" | grep -v -i api_key
  if ! echo "$out" | grep -qiE "error|outage|status code"; then echo SUBMIT_OK; exit 0; fi
  sleep 1800
done
echo SUBMIT_GAVE_UP; exit 1
