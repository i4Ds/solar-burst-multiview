#!/bin/bash
# P-AIRCARS in developer mode (https://p-aircars.readthedocs.io/en/latest/install_paircars.html),
# from a clone at ~/paircars/P-AIRCARS, into the env paircars_env next to the PyPI env paircars.
# Runs on calc-cpu (has network) so dependency builds stay off the login node:
#   git clone https://github.com/devojyoti96/P-AIRCARS.git ~/paircars/P-AIRCARS
#   sbatch -M calc-cpu ~/paircars/install/paircars-dev-install.sbatch
# Editable (-e) instead of the docs' plain .[dev], so a git pull or local fix needs no reinstall.
#SBATCH --job-name=paircars-dev
#SBATCH --partition=cpu-daily
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=02:00:00
#SBATCH --output=/scratch/%u/paircars/logs/dev-install-%j.out

set -euo pipefail
export PYTHONNOUSERSITE=1
unset PYTHONPATH
export TMPDIR="/scratch/$USER/paircars/tmp"
mkdir -p "$TMPDIR"
# shellcheck disable=SC1091
source "$HOME/paircars/miniforge3/etc/profile.d/conda.sh"

# The documented environment (activate_conda.html).
mamba create -y -n paircars_env --override-channels -c conda-forge \
  python=3.10 gcc_linux-64=14 gxx_linux-64=14 gfortran_linux-64=14 cmake pkg-config pip
conda activate paircars_env

cd "$HOME/paircars/P-AIRCARS"
git log -1 --format="P-AIRCARS %h %ad %s" --date=short
pip install -e ".[dev]"

pip show paircars | grep -E "^(Version|Editable project location)"
python -c "import paircars, casatools, casatasks, casacore; print('imports ok')"
command -v run-mwa-paircars init-paircars-setup
echo DEV_INSTALL_OK
