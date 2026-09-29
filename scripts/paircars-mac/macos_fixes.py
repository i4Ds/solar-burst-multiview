#!/usr/bin/env python3
"""Apple Silicon fixes for a P-AIRCARS install inside the linux/amd64 container.

udocker's proot engine cannot exec under Rosetta, so imaging containers use
fakechroot (F1). PostgreSQL's entrypoint expects a Unix socket, which
fakechroot cannot bind, so the server is started on TCP instead.

Run inside the container, after ``pip install`` and again after
``init-paircars-setup``:

    python3 macos_fixes.py patch-code
    python3 macos_fixes.py patch-images
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

UDOCKER_UTILS = Path(
    "/opt/miniforge3/envs/paircars/lib/python3.10/site-packages/"
    "paircars/utils/udocker_utils.py"
)

CODE_REPLACEMENTS = (
    (
        'cmd = ["udocker", "setup", "--execmode=P1", f"{container_name}"]',
        'cmd = ["udocker", "setup", "--execmode=F1", f"{container_name}"]',
    ),
    (
        '''        f"--env=POSTGRES_DB={postgres_db}",
        f"{container_name}",''',
        '''        f"--env=POSTGRES_DB={postgres_db}",
        "--env=LANG=C",
        "--env=LC_ALL=C",
        f"{container_name}",''',
    ),
    (
        '''        "-c",
        "shared_buffers=1024MB",
    ]''',
        '''        "-c",
        "shared_buffers=1024MB",
        "-c",
        f"port={postgres_port}",
        "-c",
        "unix_socket_directories=",
    ]''',
    ),
)

ENTRYPOINT_REPLACEMENTS = (
    (
        "\tls /docker-entrypoint-initdb.d/ > /dev/null\n",
        "\tls /docker-entrypoint-initdb.d/ > /dev/null || true\n",
    ),
    (
        "\tset -- \"$@\" -c listen_addresses='' -p \"${PGPORT:-5432}\"\n",
        "\tset -- \"$@\" -c listen_addresses='127.0.0.1' "
        "-c unix_socket_directories='' -p \"${PGPORT:-5432}\"\n"
        "\texport PGHOST=127.0.0.1\n",
    ),
    (
        '\tPGHOST= PGHOSTADDR= "${query_runner[@]}" "$@"\n',
        '\tPGHOST=127.0.0.1 PGHOSTADDR= "${query_runner[@]}" "$@"\n',
    ),
)


def _replace_once(path: Path, old: str, new: str) -> str:
    text = path.read_text()
    if new in text:
        return "already"
    if old not in text:
        return "missing"
    path.write_text(text.replace(old, new, 1))
    return "patched"


def patch_code() -> int:
    if not UDOCKER_UTILS.is_file():
        print(f"paircars is not installed at {UDOCKER_UTILS}", file=sys.stderr)
        return 1
    for old, new in CODE_REPLACEMENTS:
        state = _replace_once(UDOCKER_UTILS, old, new)
        print(f"udocker_utils.py {state}")
        if state == "missing":
            return 1
    return 0


def _zero_file(path: Path) -> bool:
    if path.is_symlink() or not path.exists():
        return False
    st = path.stat()
    return st.st_size == 0 and not path.is_dir()


def _replace_empty_with_symlink(path: Path, target: str) -> None:
    if path.is_symlink():
        return
    if path.exists() or path.is_file():
        if not _zero_file(path) and path.exists():
            return
        path.chmod(0o644)
        path.unlink()
    path.symlink_to(target)
    print(f"symlink {path} -> {target}")


def _fix_linker(root: Path) -> None:
    link = root / "usr/lib64/ld-linux-x86-64.so.2"
    real = root / "usr/lib/x86_64-linux-gnu/ld-linux-x86-64.so.2"
    if real.is_file() and _zero_file(link):
        _replace_empty_with_symlink(link, "../lib/x86_64-linux-gnu/ld-linux-x86-64.so.2")


def _write_execmode(container_dir: Path) -> None:
    mode = container_dir / "execmode"
    if mode.is_file() and mode.read_text().strip() == "F1":
        return
    mode.write_text("F1\n")
    print(f"execmode F1 {container_dir.name}")


def _fix_postgres(root: Path) -> None:
    mawk = root / "usr/bin/mawk"
    if mawk.is_file():
        _replace_empty_with_symlink(root / "usr/bin/awk", "mawk")
        _replace_empty_with_symlink(root / "bin/awk", "mawk")
    run = root / "run"
    if run.is_dir():
        run.chmod(0o777)
        sock = run / "postgresql"
        sock.mkdir(exist_ok=True)
        sock.chmod(0o777)
    _replace_empty_with_symlink(root / "var/run", "../run")
    _replace_empty_with_symlink(root / "var/lock", "../run/lock")
    sample = root / "usr/share/postgresql/postgresql.conf.sample"
    versioned = root / "usr/share/postgresql/18/postgresql.conf.sample"
    if sample.is_file() and sample.stat().st_size > 0 and (
        not versioned.exists() or versioned.stat().st_size == 0
    ):
        if versioned.exists() and not versioned.is_symlink():
            versioned.chmod(0o644)
        versioned.write_bytes(sample.read_bytes())
        versioned.chmod(0o644)
        print(f"restored {versioned}")
    for rel in ("usr/share/postgresql", "usr/lib/postgresql", "usr/bin"):
        base = root / rel
        if not base.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            current = Path(dirpath)
            mode = current.stat().st_mode
            if (mode & 0o555) != 0o555:
                current.chmod(mode | 0o755)
            for name in filenames:
                path = current / name
                if path.is_symlink():
                    continue
                try:
                    mode = path.stat().st_mode
                except OSError:
                    continue
                if (mode & 0o444) != 0o444:
                    path.chmod(mode | 0o644)
    entry = root / "usr/local/bin/docker-entrypoint.sh"
    if not entry.is_file():
        print(f"postgres entrypoint missing: {entry}", file=sys.stderr)
        return
    for old, new in ENTRYPOINT_REPLACEMENTS:
        state = _replace_once(entry, old, new)
        print(f"docker-entrypoint.sh {state}")
    data = root / "var/lib/postgresql/data"
    if data.is_dir():
        data.chmod(0o777)
    host_sock = Path("/run/postgresql")
    host_sock.mkdir(exist_ok=True)
    host_sock.chmod(0o777)


def patch_images(udocker_dir: Path) -> int:
    containers = udocker_dir / "containers"
    if not containers.is_dir():
        print(f"udocker containers not found: {containers}", file=sys.stderr)
        return 1
    seen: set[Path] = set()
    for child in containers.iterdir():
        target = child.resolve()
        root = target / "ROOT"
        if not root.is_dir() or target in seen:
            continue
        seen.add(target)
        _write_execmode(target)
        _fix_linker(root)
    postgres = containers / "paircarspostgres"
    if not postgres.exists():
        print("paircarspostgres container is missing", file=sys.stderr)
        return 1
    _fix_postgres(postgres.resolve() / "ROOT")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("patch-code")
    images = sub.add_parser("patch-images")
    images.add_argument(
        "--udocker-dir",
        type=Path,
        default=Path("/data/meta/paircarspipe_data/udocker"),
    )
    args = parser.parse_args()
    if args.cmd == "patch-code":
        return patch_code()
    return patch_images(args.udocker_dir)


if __name__ == "__main__":
    raise SystemExit(main())
