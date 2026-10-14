#!/bin/bash
# Short-baseline test: image a P-AIRCARS-calibrated MS twice with the wsclean
# command P-AIRCARS used, (a) as is and (b) with short baselines thinned to the
# counts of a reference layout (uv_thin.py).
#   sbatch -M calc-cpu --export=ALL,CALMS=<calibrated ms>,ILOG=<P-AIRCARS imaging log>,REF=<uv npz>,OUT=<dir> uv_test.sbatch
#SBATCH -p cpu-daily
#SBATCH --time=04:00:00
#SBATCH -n1 -c8 --mem=32G
#SBATCH -J uv-test
#SBATCH -o /home2/andre_csillaghy/mwa/logs/%x_%j.log
set -euo pipefail
source ~/mwa/mwa-env.sh
R() { singularity exec --bind /scratch --env OPENBLAS_NUM_THREADS=1 "$MWA_DEMO_SIF" "$@"; }
mkdir -p "$OUT"; cd "$OUT"
rm -rf all.ms thin.ms
cp -a "$CALMS" all.ms; cp -a "$CALMS" thin.ms
R python3 ~/overnight/bin/uv_thin.py thin.ms "$REF"
R python3 ~/overnight/bin/uv_hist.py all.ms uv_all.npz
R python3 ~/overnight/bin/uv_hist.py thin.ms uv_thin.npz
cmd=$(grep -m1 -oE "wsclean .*" "$ILOG" | sed -E 's/ -name [^ ]+//; s/ [^ ]+\.ms$//; s/-j 1 /-j 8 /; s/-abs-mem [0-9.]+ /-abs-mem 24 /')
echo "wsclean args: $cmd"
for v in all thin; do
  R $cmd -name "$OUT/$v" "$OUT/$v.ms" > "wsclean_$v.log" 2>&1 || { tail -20 "wsclean_$v.log"; exit 1; }
done
ls -l "$OUT"/*-image.fits
echo UVTEST_OK
