#!/bin/bash
#SBATCH -M calc-cpu
#SBATCH -p cpu-daily
#SBATCH --time=23:50:00
#SBATCH -n1 -c1 --mem=1G
#SBATCH -J asvo-2015-retry
#SBATCH -o /home2/andre_csillaghy/mwa/logs/%x_%j.log
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=andre.csillaghy@fhnw.ch
# Submit ASVO conversion jobs, retrying every 30 min while ASVO refuses (e.g. outage).
# Env: OBSIDS, PARAMS.
source ~/mwa/mwa-env.sh
export MWA_ASVO_API_KEY=$(<~/.config/mwa_asvo/api_key)
for i in $(seq 46); do
  out=$(singularity exec $MWA_DEMO_SIF giant-squid submit-conv -p "$PARAMS" $OBSIDS 2>&1)
  echo "$(date "+%F %T") attempt $i"; echo "$out" | grep -v -i api_key
  if ! echo "$out" | grep -qiE "error|outage|status code"; then echo SUBMIT_OK; exit 0; fi
  sleep 1800
done
echo SUBMIT_GAVE_UP; exit 1
