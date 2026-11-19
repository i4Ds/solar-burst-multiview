#!/bin/bash
# Phase-only CASA bandpass on Cen A, applycal on the 0.5 s Sun.
# Four Figure 4 channel pairs. No P-AIRCARS.
#
#   sbatch -M calc-cpu ~/mwa/sharma2020/quiet-noon-bandpass.sbatch
#
#SBATCH --job-name=qn-bandpass
#SBATCH --partition=cpu-daily
#SBATCH --time=04:00:00
#SBATCH -n1 -c4 --mem=16G
#SBATCH --array=0-3
#SBATCH --output=/home2/andre_csillaghy/mwa/logs/%x_%A_%a.log
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=andre.csillaghy@fhnw.ch

set -euo pipefail
source "$HOME/paircars/env.sh"

PAIRS=(84-85 125-126 169-170 187-188)
export SUN_OBS="${SUN_OBS:-1133236216}"
export CAL_OBS="${CAL_OBS:-1133236576}"
CODE="${PAPER_CODE:-$HOME/mwa/sharma2020}"
export PYTHONPATH="$CODE"

idx="${SLURM_ARRAY_TASK_ID:-0}"
python "$CODE/solve_cena_bandpass.py" "${PAIRS[$idx]}"
echo "QN_BANDPASS_OK ${PAIRS[$idx]}"
