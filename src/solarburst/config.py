"""Load YAML pipeline configs from `configs/`."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIGS_DIR = REPO_ROOT / "configs"
DATA_DIR = REPO_ROOT / "data"


def load(name: str = "sharma2022") -> dict[str, Any]:
    """Return the named YAML config as a dict.

    `name` may be a stem (`"sharma2022"`), a filename, or an absolute path.
    """
    path = Path(name)
    if not path.suffix:
        path = CONFIGS_DIR / f"{name}.yaml"
    elif not path.is_absolute():
        candidate = CONFIGS_DIR / path.name
        path = candidate if candidate.exists() else path
    with path.open() as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"config {path} did not parse to a mapping")
    return data


def local_root(cfg: dict[str, Any]) -> Path:
    """Staging directory for this event, e.g. `data/sharma2022/`."""
    return DATA_DIR / cfg["event"]["name"]


def local_path(cfg: dict[str, Any], relpath: str) -> Path:
    """Local counterpart of a path relative to `remote.rohit_root`."""
    return local_root(cfg) / relpath


def remote_uri(cfg: dict[str, Any], relpath: str) -> str:
    """`user@host:/rohit_root/<relpath>` suitable for rsync/scp."""
    remote = cfg["remote"]
    root = remote["rohit_root"].rstrip("/")
    return f"{remote['user']}@{remote['host']}:{root}/{relpath.lstrip('/')}"
