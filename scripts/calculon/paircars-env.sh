# P-AIRCARS on calculon. Source this; do not execute it.
# The conda env lives on $HOME (NFS, visible on every node). Beam files,
# udocker images, and job scratch live on BeeGFS.

export PAIRCARS_ROOT="${PAIRCARS_ROOT:-$HOME/paircars}"
export PAIRCARS_PREFIX="$PAIRCARS_ROOT/miniforge3"
export PAIRCARS_DATA="${PAIRCARS_DATA:-/scratch/$USER/paircars}"

# P-AIRCARS calls sinfo and sbatch with no cluster flag. cpu-daily exists
# only on calc-cpu. The GPU cluster is the default client cluster.
export SLURM_CLUSTERS="${SLURM_CLUSTERS:-calc-cpu}"

export PYTHONNOUSERSITE=1
unset PYTHONPATH

mkdir -p "$PAIRCARS_DATA/tmp" "$PAIRCARS_DATA/work" "$PAIRCARS_DATA/logs" "$PAIRCARS_DATA/out"
export TMPDIR="$PAIRCARS_DATA/tmp"
export TMP="$TMPDIR"
export TEMP="$TMPDIR"

# shellcheck disable=SC1091
source "$PAIRCARS_PREFIX/etc/profile.d/conda.sh"
# paircars_env: developer-mode install from ~/paircars/P-AIRCARS (paircars-dev-install.sbatch).
# PAIRCARS_ENV=paircars selects the older PyPI 3.0.6 env.
conda activate "${PAIRCARS_ENV:-paircars_env}"
