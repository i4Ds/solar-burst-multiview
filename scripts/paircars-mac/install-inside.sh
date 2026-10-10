#!/bin/bash
# Install P-AIRCARS inside the linux/amd64 Ubuntu container. Invoked by setup.sh.
set -euo pipefail

SKIP_INIT="${SKIP_INIT:-0}"
FIXES="${PAIRCARS_FIXES:-/tmp/macos_fixes.py}"

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends \
  build-essential ca-certificates curl git pkg-config \
  libssl-dev libgl1 libglib2.0-0 libxkbcommon0 libdbus-1-3 \
  libxcb-xinerama0 libcurl4 wget bzip2 libgfortran5 gfortran cmake

if [[ ! -x /opt/miniforge3/bin/conda ]]; then
  curl -fsSLo /tmp/miniforge.sh \
    https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh
  bash /tmp/miniforge.sh -b -p /opt/miniforge3
  rm -f /tmp/miniforge.sh
fi

# shellcheck disable=SC1091
source /opt/miniforge3/etc/profile.d/conda.sh
if [[ ! -d /opt/miniforge3/envs/paircars ]]; then
  conda create -y -n paircars --override-channels -c conda-forge \
    python=3.10 gcc_linux-64=14 gxx_linux-64=14 gfortran_linux-64=14 \
    cmake pkg-config pip
fi
conda activate paircars

if ! id paircars >/dev/null 2>&1; then
  useradd -m -s /bin/bash paircars
fi
chmod -R a+rX /opt/miniforge3
chmod -R a+rwX /data

export PYTHONNOUSERSITE=1
unset PYTHONPATH || true
if ! python -c "import paircars" >/dev/null 2>&1; then
  pip install "/opt/P-AIRCARS[dev]"
fi
python "$FIXES" patch-code
mkdir -p /opt/miniforge3/envs/paircars/lib/python3.10/site-packages/prefect/server/ui_build
chmod 777 /opt/miniforge3/envs/paircars/lib/python3.10/site-packages/prefect/server/ui_build

run_init() {
  su -s /bin/bash paircars -c \
    "export HOME=/home/paircars USER=paircars PYTHONUNBUFFERED=1 PYTHONNOUSERSITE=1 QT_QPA_PLATFORM=offscreen MPLBACKEND=Agg; \
     source /opt/miniforge3/etc/profile.d/conda.sh && conda activate paircars && \
     cd /data/work && init-paircars-setup --init --configdir /data/meta"
}

if [[ "$SKIP_INIT" != "1" ]]; then
  install -d -o paircars -g paircars /data/work
  # The first pass extracts udocker images, then PostgreSQL fails until the
  # fakechroot fixes below exist. The second pass skips the beam build.
  set +e
  run_init
  init_rc=$?
  set -e
  python "$FIXES" patch-images
  if [[ "$init_rc" -ne 0 ]]; then
    run_init
  fi
elif [[ -d /data/meta/paircarspipe_data/udocker/containers ]]; then
  python "$FIXES" patch-images
fi

echo "P-AIRCARS Mac container install finished."
