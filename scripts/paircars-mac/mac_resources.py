"""Resource ceilings for P-AIRCARS inside the Apple Silicon virtual machine.

Upstream clamps a local worker to 80% of whatever machine it can see. That
limit is for a shared cluster node. This virtual machine runs P-AIRCARS
only, so a request of 0.8 means "the maximum the guest can spare".

The Apple GPU is not part of the calculation. The imaging command in this
install is WSClean ``-gridder wgridder`` (CPU). IDG's GPU mode is CUDA.
"""

from __future__ import annotations

import os
from pathlib import Path

MARKER = Path("/etc/paircars-mac-cap")
OLD_CEILING = 0.8
# Leave a slice of the guest for the kernel even if the reserve is set to 0.
HARD_CEILING = 0.95


def fractions(
    ncpu,
    total_gib,
    cpu_frac,
    mem_frac,
    *,
    cap=None,
    enabled=False,
    reserve_cpu=1,
    reserve_gib=4.0,
):
    """Return ``(cpu_frac, mem_frac)`` after the Mac ceiling.

    A requested fraction at or above 0.8 is the upstream maximum, so the
    Mac ceiling replaces it. A lower request, such as the sample run's
    0.5, is left alone.
    """
    requested_cpu = abs(float(cpu_frac))
    requested_mem = abs(float(mem_frac))
    if cap is not None and str(cap).strip() != "":
        ceiling = min(1.0, abs(float(cap)))
        return _apply(requested_cpu, ceiling), _apply(requested_mem, ceiling)
    if not enabled:
        return (
            min(requested_cpu, OLD_CEILING),
            min(requested_mem, OLD_CEILING),
        )
    ncpu = max(1, int(ncpu))
    usable_cpu = max(1, ncpu - max(0, int(reserve_cpu)))
    cpu_ceiling = min(HARD_CEILING, max(OLD_CEILING, usable_cpu / ncpu))
    reserve_gib = max(0.0, float(reserve_gib))
    if float(total_gib) <= reserve_gib:
        mem_ceiling = OLD_CEILING
    else:
        mem_ceiling = min(
            HARD_CEILING,
            max(OLD_CEILING, (float(total_gib) - reserve_gib) / float(total_gib)),
        )
    return _apply(requested_cpu, cpu_ceiling), _apply(requested_mem, mem_ceiling)


def _apply(requested, ceiling):
    if requested >= OLD_CEILING - 1e-9:
        return ceiling
    return min(requested, ceiling)


def _marker_reserves():
    reserve_cpu = 1
    reserve_gib = 4.0
    if not MARKER.is_file():
        return False, reserve_cpu, reserve_gib
    for line in MARKER.read_text().splitlines():
        if line.startswith("reserve_cpu="):
            reserve_cpu = int(line.split("=", 1)[1].strip())
        elif line.startswith("reserve_gib="):
            reserve_gib = float(line.split("=", 1)[1].strip())
    if "PAIRCARS_RESERVE_CPU" in os.environ:
        reserve_cpu = int(os.environ["PAIRCARS_RESERVE_CPU"])
    if "PAIRCARS_RESERVE_GB" in os.environ:
        reserve_gib = float(os.environ["PAIRCARS_RESERVE_GB"])
    return True, reserve_cpu, reserve_gib


def clamp_fracs(cpu_frac, mem_frac, ncpu=None, total_gib=None):
    """Ceiling used by ``get_local_dask_cluster`` inside the container."""
    import psutil

    if ncpu is None:
        ncpu = psutil.cpu_count() or 1
    if total_gib is None:
        total_gib = psutil.virtual_memory().total / 1024**3
    enabled, reserve_cpu, reserve_gib = _marker_reserves()
    return fractions(
        ncpu,
        total_gib,
        cpu_frac,
        mem_frac,
        cap=os.environ.get("PAIRCARS_RESOURCE_CAP"),
        enabled=enabled,
        reserve_cpu=reserve_cpu,
        reserve_gib=reserve_gib,
    )


def _self_check():
    # 16 vCPU guest, ~39 GiB visible, request at the upstream maximum.
    cpu, mem = fractions(16, 39.09, 0.8, 0.8, enabled=True)
    assert abs(cpu - 15 / 16) < 1e-9, cpu
    assert abs(mem - (39.09 - 4) / 39.09) < 1e-9, mem
    assert int(16 * cpu) == 15
    # Sample run asks for less than the ceiling.
    cpu, mem = fractions(16, 39.09, 0.5, 0.6, enabled=True)
    assert cpu == 0.5 and mem == 0.6
    # No marker: upstream 80% clamp.
    cpu, mem = fractions(16, 39.09, 0.95, 0.95, enabled=False)
    assert cpu == 0.8 and mem == 0.8
    # Explicit cap replaces the 0.8 request and is allowed up to 1.
    cpu, mem = fractions(16, 39.09, 0.8, 0.8, cap="1")
    assert cpu == 1.0 and mem == 1.0
    print("mac_resources self-check ok")


if __name__ == "__main__":
    _self_check()
