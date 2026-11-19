#!/bin/bash
# Oberoi S_odot (Haslam at this pointing) plus the Fig. 4 two-row PNG
# from the 570-frame SuperUniform cubes. paircars env (astropy_healpix).
#
#   sbatch -M calc-cpu ~/mwa/sharma2020/sharma2020-raw-rohit-figure.sbatch
#
#SBATCH --job-name=so2020-raw-fig
#SBATCH --partition=cpu-daily
#SBATCH --time=04:00:00
#SBATCH -n1 -c8 --mem=32G
#SBATCH --output=/home2/andre_csillaghy/mwa/logs/%x_%j.log
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=andre.csillaghy@fhnw.ch

set -euo pipefail
source "$HOME/paircars/env.sh"

CODE="${PAPER_CODE:-$HOME/mwa/sharma2020}"
export PYTHONPATH="$CODE"
# solarburst.config.REPO_ROOT is parents[2] of solarburst/config.py → ~/mwa
mkdir -p "$HOME/mwa/data/haslam" "$HOME/mwa/data/quiet2015" "$HOME/mwa/figures/sharma2020"
cp -n "$CODE/data/haslam/lambda_haslam408_nofilt.fits" "$HOME/mwa/data/haslam/" || true
cp -n "$CODE/data/quiet2015/fig4_tb_perframe.npz" "$HOME/mwa/data/quiet2015/" || true

FLUX=/scratch/$USER/mwa/sharma2020/raw/flux_rohitcal
FRAMES=/scratch/$USER/mwa/sharma2020/raw/casa_su_rohitcal
mkdir -p "$FLUX"
cd "$FLUX"
export OPENBLAS_NUM_THREADS=1

for item in "108 84-85" "162 125-126" "217 169-170" "240 187-188"; do
  set -- $item
  LABEL=$1 PAIR=$2
  MS=/scratch/$USER/mwa/sharma2020/raw/cal_0p5s_casa/1133149192_ch${PAIR}_0p5s.ms
  outj="$FLUX/${LABEL}MHz_full.json"
  if [[ -s "$outj" ]]; then
    echo "FLUX $LABEL reuse"
    continue
  fi
  echo "FLUX $LABEL"
  python "$CODE/sharma2020_oberoi_flux.py" \
    "$MS" "$outj" --column CORRECTED_DATA --sky haslam
done

python "$CODE/sharma2020_fig4_visuals.py" \
  --ours-dir "$FRAMES" \
  --flux-dir "$FLUX" \
  --cache /scratch/$USER/mwa/sharma2020/raw/fig4_raw_tb.npz \
  --tag raw

echo "RAW_ROHIT_FIG_OK"
ls -l "$HOME/mwa/figures/sharma2020/fig4_his_vs_raw"*.png
