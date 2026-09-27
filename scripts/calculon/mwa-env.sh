# Paths and image URIs for the MWA containers on calculon.
# Source this; do not execute it. Slurm copies batch scripts to a spool
# directory, so batch scripts source the installed copy at $HOME/mwa/mwa-env.sh.

# Login node has no container runtime. CPU nodes (cluster calc-cpu) provide
# Apptainer 1.5, exposed as `singularity`. GPU nodes (cluster `cluster`)
# provide Singularity-CE 4.3.1 with --nv. A SIF built on the CPU side runs
# on the GPU side. $HOME is the same NFS mount on both.

export MWA_ROOT="${MWA_ROOT:-$HOME/mwa}"
export MWA_IMAGES="$MWA_ROOT/images"
export MWA_SMOKE="$MWA_ROOT/smoke"
export MWA_CACHE="${MWA_CACHE:-/scratch/$USER/mwa/cache}"
export MWA_TMP="${MWA_TMP:-/scratch/$USER/mwa/tmp}"

export APPTAINER_CACHEDIR="$MWA_CACHE"
export APPTAINER_TMPDIR="$MWA_TMP"
export SINGULARITY_CACHEDIR="$MWA_CACHE"
export SINGULARITY_TMPDIR="$MWA_TMP"

# André's interactive smoke-test image (hyperdrive vis-sim).
export HYPERDRIVE_SIF="$MWA_IMAGES/hyperdrive_0.6.1-autos-cuda12.5.1-ubuntu24.04.sif"
export HYPERDRIVE_URI="docker://mwatelescope/hyperdrive:0.6.1-autos-cuda12.5.1-ubuntu24.04"

# Official MWA stack: hyperdrive base plus birli, giant-squid, wsclean,
# EveryBeam, IDG, CHIPS, AOFlagger, SSINS.
# https://github.com/MWATelescope/mwa-demo/blob/main/Dockerfile
export MWA_DEMO_SIF="$MWA_IMAGES/mwa-demo_cuda12.5.1.sif"
export MWA_DEMO_URI="docker://mwatelescope/mwa-demo:cuda12.5.1"

# Swiss Karabo/Spack image (hyperdrive, wsclean, aoflagger, DP3).
# Built for Daint and Besso; same digest here.
export SWISS_SIF="$MWA_IMAGES/sp5505_sha-967aa66-pass.sif"
export SWISS_URI="docker://ghcr.io/d3v-null/sp5505:sha-967aa66-pass"

mwa_mkdirs() {
  mkdir -p "$MWA_IMAGES" "$MWA_SMOKE" "$MWA_CACHE" "$MWA_TMP" "$MWA_ROOT/logs"
}
