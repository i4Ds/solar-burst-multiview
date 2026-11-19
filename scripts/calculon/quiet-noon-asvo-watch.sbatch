#!/bin/bash
# Wait until the 4 December 2015 ASVO conversions are Ready, then download.
#
#   sbatch -M calc-cpu ~/mwa/sharma2020/quiet-noon-asvo-watch.sbatch
#
#SBATCH --job-name=qn-asvo-watch
#SBATCH --partition=cpu-daily
#SBATCH --time=23:59:00
#SBATCH -n1 -c1 --mem=2G
#SBATCH --output=/home2/andre_csillaghy/mwa/logs/%x_%j.log
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=andre.csillaghy@fhnw.ch

set -euo pipefail
source "$HOME/mwa/mwa-env.sh"
export MWA_ASVO_API_KEY=$(<"$HOME/.config/mwa_asvo/api_key")
gs() { singularity exec -B /mnt/nas05/data02 "$MWA_DEMO_SIF" giant-squid "$@"; }

SUN_OBS=1133236216
CAL_OBS=1133236576
SUN_JOB=1124591
CAL_JOB=1124592
DEST=/mnt/nas05/data02/MWA_data/data/mwa_data2
DL="$HOME/mwa/asvo-download-retry.sbatch"

job_state() {
  gs list "$1" 2>/dev/null | awk -F'|' -v id="$1" '$2 ~ id {gsub(/ /,"",$5); print $5}'
}

job_bytes() {
  # giant-squid prints e.g. "50.9 GiB"; require 98% of that so rounding cannot stall.
  gs list "$1" 2>/dev/null | python3 -c "
import sys
job=sys.argv[1]
for line in sys.stdin:
    if job not in line or 'Ready' not in line:
        continue
    parts=[p.strip() for p in line.split('|')]
    if len(parts)<6:
        continue
    tok=parts[5].split()
    if len(tok)<2:
        continue
    val=float(tok[0]); unit=tok[1].lower()
    mul={'gib':1024**3,'mib':1024**2,'tib':1024**4}.get(unit,1)
    print(int(val*mul*0.98))
    break
" "$1"
}

echo "$(date -Is) watching $SUN_JOB (Sun) and $CAL_JOB (Cen A)"
for i in $(seq 1 90); do
  sun_st=$(job_state "$SUN_JOB" || true)
  cal_st=$(job_state "$CAL_JOB" || true)
  echo "$(date -Is) attempt $i  Sun=$sun_st  CenA=$cal_st"
  if [[ "${sun_st:-}" == Ready && "${cal_st:-}" == Ready ]]; then
    sun_b=$(job_bytes "$SUN_JOB")
    cal_b=$(job_bytes "$CAL_JOB")
    echo "bytes Sun=$sun_b CenA=$cal_b"
    [[ -n $sun_b && -n $cal_b ]] || { echo "could not parse sizes"; exit 1; }
    sbatch -M calc-cpu --time=23:59:00 --export=ALL,JOBID=$SUN_JOB,OBSID=$SUN_OBS,KIND=ms,BYTES=$sun_b \
      "$DL"
    sbatch -M calc-cpu --time=23:59:00 --export=ALL,JOBID=$CAL_JOB,OBSID=$CAL_OBS,KIND=ms,BYTES=$cal_b \
      "$DL"
    echo WATCH_SUBMITTED_DOWNLOADS
    exit 0
  fi
  if echo "${sun_st:-} ${cal_st:-}" | grep -qiE 'Error|Cancelled|Expired'; then
    echo "ASVO failed: Sun=$sun_st CenA=$cal_st"
    exit 1
  fi
  sleep 900
done
echo "$(date -Is) still not Ready after 90 polls"
exit 1
