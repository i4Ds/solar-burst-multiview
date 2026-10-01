#!/bin/bash
# One-time P-AIRCARS init: Zenodo metadata, beam interpolation, udocker images.
# Submit on cluster calc-cpu (see submit-paircars.sh). CPU nodes are Rocky
# Linux 9; the login node is Ubuntu 24.04. Official support is Ubuntu 22/24
# and CentOS 7. This job is the check that casatools and udocker run here.
#SBATCH --job-name=paircars-init
#SBATCH --partition=cpu-daily
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=12:00:00
#SBATCH --output=/scratch/%u/paircars/logs/init-%j.out

set -euo pipefail
# shellcheck disable=SC1091
source "$HOME/paircars/env.sh"
cd "$PAIRCARS_DATA/work"
python -c "import casatools, paircars; print('import-ok', casatools.__file__)"
# PyPI paircars 3.0.6. The git tree calls this flag --configdir.
init-paircars-setup --init --datadir "$PAIRCARS_DATA/meta"
echo INIT_OK
