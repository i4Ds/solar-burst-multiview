#!/bin/bash
# One 4 s MWA image of the Sun nearest PEAK_UTC, for the 2022-09-30 flares.
# Defaults: solar obs 1348545200, calibrator 1348522216 (PKS0408-65), ch113.
# From 1348547272 on the series uses ch101-187; calibrate those with 3C444 (1348574416).
# Submit from ~/mwa:
#   sbatch --export=ALL,CHANNEL=113 ~/mwa/flare/flare-image.sbatch
#   sbatch --export=ALL,SUN_OBSID=1348547272,CAL_OBSID=1348574416,CHANNEL=112,PEAK_UTC=2022-09-30T04:28:36 \
#     ~/mwa/flare/flare-image.sbatch
# Inputs are extracted from the archive tarballs into $root (never written in place).
# The ASVO MSs are averaged to 4 s and 160 kHz, so one timestep is the shortest image.
#SBATCH --job-name=mwa-flare
#SBATCH --partition=p3080
#SBATCH --gres=gpu:rtx3080:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=24G
#SBATCH --time=01:00:00
#SBATCH --output=logs/%x_%j.log

set -euo pipefail
source "$HOME/mwa/mwa-env.sh"

CHANNEL="${CHANNEL:-113}"
PEAK_UTC="${PEAK_UTC:-2022-09-30T03:57:23}"
SUN_OBSID="${SUN_OBSID:-1348545200}"
CAL_OBSID="${CAL_OBSID:-1348522216}"
archive=/mnt/nas05/data02/MWA_data/data/mwa_data
root="/scratch/${USER}/mwa/flare20220930"
src="$HOME/mwa/cal/GGSM_updated.fits"
beam="$HOME/mwa/smoke/mwa_full_embedded_element_pattern.h5"

cd "$root"
for id in "$SUN_OBSID" "$CAL_OBSID"; do
  tars=( "$archive"/${id}_*_ms.tar )
  [[ -d ${id}_ch${CHANNEL}.ms ]] || tar -xf "${tars[0]}" "./${id}.metafits" "./${id}_ch${CHANNEL}.ms"
done

sol="cal/hyp_soln_${CAL_OBSID}_ch${CHANNEL}.fits"
cms="${SUN_OBSID}_ch${CHANNEL}_cal.ms"
tag="${PEAK_UTC:11:8}"
img="img/${SUN_OBSID}_ch${CHANNEL}_${tag//:/}"
mkdir -p cal img

echo "node=$(hostname) channel=${CHANNEL} peak=${PEAK_UTC}"
nvidia-smi -L
export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK}"
run() { singularity exec --nv --env OPENBLAS_NUM_THREADS=1,MWA_BEAM_FILE="$beam" "$MWA_DEMO_SIF" "$@"; }

if [[ ! -s $sol ]]; then
  run hyperdrive di-calibrate \
    --source-list "$src" \
    --data "${CAL_OBSID}_ch${CHANNEL}.ms" "${CAL_OBSID}.metafits" \
    --outputs "$sol.partial.fits"
  mv "$sol.partial.fits" "$sol"
fi

if [[ ! -d $cms ]]; then
  run hyperdrive solutions-apply \
    --data "${SUN_OBSID}_ch${CHANNEL}.ms" "${SUN_OBSID}.metafits" \
    --solutions "$sol" \
    --outputs "$cms"
fi

# Timestep index from the TIME column, and the apparent Sun position at the peak.
read -r idx tstep sunpos < <(run python3 - "$cms" "$PEAK_UTC" <<'EOF'
import sys, numpy as np
from casacore.tables import table
from astropy.time import Time
from astropy.coordinates import get_body, EarthLocation
import astropy.units as u
ms, peak = sys.argv[1], Time(sys.argv[2], scale="utc")
tt = np.unique(table(ms, ack=False).getcol("TIME"))
i = int(np.argmin(np.abs(tt - peak.mjd * 86400)))
mwa = EarthLocation.from_geodetic(116.67081524 * u.deg, -26.70331940 * u.deg, 377.83 * u.m)
# Apparent (topocentric GCRS) RA/Dec. Do not convert to ICRS: that is barycentric and
# puts the Sun ~11° away through parallax.
sun = get_body("sun", peak, mwa)
print(i, Time(tt[i] / 86400, format="mjd").isot,
      sun.to_string("hmsdms", precision=2))
EOF
)
echo "timestep=${idx} centre=${tstep} sun=${sunpos}"

run wsclean -version | head -2
run wsclean \
  -name "$img" \
  -interval "$idx" "$((idx + 1))" \
  -shift ${sunpos} \
  -size 1024 1024 -scale 10asec \
  -pol I -weight briggs 0 \
  -niter 5000 -mgain 0.85 -auto-threshold 3 -auto-mask 5 \
  -multiscale \
  -j "${SLURM_CPUS_PER_TASK}" \
  "$cms"

ls -lh "${img}"*.fits
echo FLARE_IMAGE_DONE
