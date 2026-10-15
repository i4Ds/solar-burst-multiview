#!/bin/bash
# Image P-AIRCARS-calibrated MSs with two sets of wsclean settings:
#   s2022: the command P-AIRCARS used for the 2022 data (from ILOG), without -interval;
#   s2015: the same with the 2015 values (pixel 44.2", 442 px, maxuv 1401.2 lambda,
#          Tukey taper 234.2 lambda, multiscale 0,4,10 / bias 0.764).
# Each for the last MS alone ("short") and for all MSs together ("long").
#   sbatch -M calc-cpu --export=ALL,ILOG=<log>,OUT=<dir>,MSS="<ms> <ms> ..." quiet_settings.sbatch
#SBATCH -p cpu-daily
#SBATCH --time=06:00:00
#SBATCH -n1 -c8 --mem=48G
#SBATCH -J quiet-settings
#SBATCH -o /home2/andre_csillaghy/mwa/logs/%x_%j.log
set -euo pipefail
source ~/mwa/mwa-env.sh
R() { singularity exec --bind /scratch --env OPENBLAS_NUM_THREADS=1 "$MWA_DEMO_SIF" "$@"; }
mkdir -p "$OUT"; cd "$OUT"
read -r -a ms <<< "$MSS"
base=$(grep -m1 -oE "wsclean .*" "$ILOG" | sed -E 's/ -name [^ ]+//; s/ [^ ]+\.ms$//; s/ -interval [0-9]+ [0-9]+//; s/-j 1 /-j 8 /; s/-abs-mem [0-9.]+ /-abs-mem 40 /')
s2015=$(echo "$base" | sed -E 's/-scale [^ ]+/-scale 44.2asec/; s/-size [0-9]+ [0-9]+/-size 442 442/; s/-maxuv-l [0-9.]+/-maxuv-l 1401.2/; s/-taper-tukey [0-9.]+/-taper-tukey 234.2/; s/-multiscale-scales [^ ]+/-multiscale-scales 0,4,10/; s/-multiscale-scale-bias [0-9.]+/-multiscale-scale-bias 0.764/')
echo "s2022: $base"; echo "s2015: $s2015"
run() { R $1 -name "$OUT/$2" "${@:3}" > "wsclean_$2.log" 2>&1 || { tail -20 "wsclean_$2.log"; exit 1; }; }
run "$base"  short_s2022 "${ms[-1]}"
run "$s2015" short_s2015 "${ms[-1]}"
run "$base"  long_s2022  "${ms[@]}"
run "$s2015" long_s2015  "${ms[@]}"
ls -l "$OUT"/*-image.fits
echo SETTINGS_OK
