"""Rsync named slices from calculon into `data/<event>/`.

Paths in the YAML are relative to `remote.rohit_root`. Local copies keep that
relative layout so notebooks never hardcode a machine-specific prefix.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from solarburst.config import load, local_path, local_root, remote_uri

DEFAULT_SSH_KEY = Path.home() / ".ssh" / "id_ed25519"


def _ssh_command(identity: Path | None = None) -> list[str]:
    key = identity or Path(os.environ.get("SOLARBURST_SSH_KEY", DEFAULT_SSH_KEY))
    cmd = ["ssh", "-o", "BatchMode=yes"]
    if key.exists():
        cmd.extend(["-i", str(key), "-o", "IdentitiesOnly=yes"])
    return cmd


def rsync_remote(
    cfg: dict,
    relpath: str,
    *,
    identity: Path | None = None,
) -> Path:
    """Copy `relpath` from calculon. Returns the local path.

    Measurement sets are directories; rsync copies the directory itself into
    the matching local parent so the `.ms` suffix is preserved.
    """
    dest = local_path(cfg, relpath)
    dest.parent.mkdir(parents=True, exist_ok=True)
    source = remote_uri(cfg, relpath)
    ssh = " ".join(_ssh_command(identity))
    cmd = [
        "rsync",
        "-a",
        "--progress",
        "--partial",
        "--timeout=120",
        "--exclude=table.lock",
        "-e",
        ssh,
        source,
        str(dest.parent) + "/",
    ]
    print(f"rsync {source} -> {dest}", file=sys.stderr)
    subprocess.run(cmd, check=True)
    if not dest.exists():
        raise FileNotFoundError(f"rsync finished but {dest} is missing")
    return dest


def stage_validation_pair(
    cfg: dict | None = None,
    *,
    identity: Path | None = None,
) -> tuple[Path, Path]:
    """Stage Sharma's subtraction input and expected output (the 1.2 GB pair)."""
    cfg = cfg or load()
    spec = cfg["validation"]["subtraction"]
    input_ms = rsync_remote(cfg, spec["input"], identity=identity)
    expected_ms = rsync_remote(cfg, spec["expected"], identity=identity)
    return input_ms, expected_ms


MAX_STAGE_BYTES = 1024 ** 4  # 1 TiB


def staged_bytes(cfg: dict) -> int:
    root = local_root(cfg)
    if not root.exists():
        return 0
    result = subprocess.run(
        ["du", "-sk", str(root)],
        check=True,
        capture_output=True,
        text=True,
    )
    return int(result.stdout.split()[0]) * 1024


def stage_bulk(
    cfg: dict | None = None,
    *,
    identity: Path | None = None,
    max_bytes: int = MAX_STAGE_BYTES,
) -> list[Path]:
    """Rsync every path in `cfg['stage']`, stopping if the 1 TiB cap is hit."""
    cfg = cfg or load()
    paths = cfg.get("stage") or []
    if not paths:
        raise ValueError("config has no `stage:` list")
    done: list[Path] = []
    for relpath in paths:
        used = staged_bytes(cfg)
        print(
            f"staged {used / 1024**3:.1f} GiB / {max_bytes / 1024**3:.0f} GiB cap",
            file=sys.stderr,
        )
        if used >= max_bytes:
            print(f"cap reached, skipping remaining including {relpath}", file=sys.stderr)
            break
        done.append(rsync_remote(cfg, relpath, identity=identity))
    return done


def open_ms(path: Path | str):
    """Open a measurement set read-only through python-casacore."""
    from casacore.tables import table

    return table(str(path), readonly=True)


def summarise_ms(path: Path | str) -> dict:
    t = open_ms(path)
    try:
        return {
            "path": str(path),
            "nrows": t.nrows(),
            "columns": t.colnames(),
        }
    finally:
        t.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Stage named slices from calculon into data/<event>/."
    )
    parser.add_argument(
        "--config",
        default="sharma2022",
        help="config stem or path (default: sharma2022)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="after staging, open both validation MS with python-casacore",
    )
    parser.add_argument(
        "--bulk",
        action="store_true",
        help="rsync every path in the config `stage:` list (up to 1 TiB)",
    )
    args = parser.parse_args(argv)

    cfg = load(args.config)
    if args.bulk:
        for path in stage_bulk(cfg):
            print(path)
        return 0
    input_ms, expected_ms = stage_validation_pair(cfg)
    print(input_ms)
    print(expected_ms)
    if args.check:
        for path in (input_ms, expected_ms):
            info = summarise_ms(path)
            print(f"{info['nrows']} rows, {len(info['columns'])} columns: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
