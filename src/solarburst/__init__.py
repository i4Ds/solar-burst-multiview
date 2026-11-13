"""Visibility-subtraction imaging of solar radio bursts."""

from __future__ import annotations

__all__ = ["load", "jybeam_to_tb"]


def __getattr__(name: str):
    if name == "load":
        from solarburst.config import load

        return load
    if name == "jybeam_to_tb":
        from solarburst.maps import jybeam_to_tb

        return jybeam_to_tb
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
