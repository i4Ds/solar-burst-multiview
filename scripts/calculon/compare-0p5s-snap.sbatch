#!/bin/bash
#SBATCH --job-name=so2020-0p5s-cmp
#SBATCH --partition=cpu-daily
#SBATCH --time=01:00:00
#SBATCH -n1 -c8 --mem=48G
#SBATCH --output=/home2/andre_csillaghy/mwa/logs/%x_%j.log
#SBATCH --mail-type=NONE

set -euo pipefail
source "$HOME/paircars/env.sh"
export OPENBLAS_NUM_THREADS=1
python "$HOME/mwa/sharma2020/compare_0p5s_snap.py"
