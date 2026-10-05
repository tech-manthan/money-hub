"""Configuration loading: moneyhub.yaml, optionally overridden by moneyhub.local.yaml and env."""
from __future__ import annotations

import copy
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from .paths import REPO_ROOT


def _deep_merge(base: dict, extra: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in (extra or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


class Config:
    def __init__(self, data: dict[str, Any], root: Path):
        self.data = data
        self.root = root

    def get(self, dotted: str, default: Any = None) -> Any:
        cur: Any = self.data
        for part in dotted.split("."):
            if not isinstance(cur, dict) or part not in cur:
                return default
            cur = cur[part]
        return cur

    @property
    def output_dir(self) -> Path:
        p = Path(os.environ.get("MONEYHUB_OUT") or self.data.get("output_dir", "out"))
        return p if p.is_absolute() else self.root / p

    @property
    def db_path(self) -> Path:
        return self.output_dir / "catalog.sqlite"


def load_config(root: Path | None = None) -> Config:
    root = root or Path(os.environ.get("MONEYHUB_HOME") or REPO_ROOT)
    data: dict[str, Any] = {}
    for name in ("moneyhub.yaml", "moneyhub.local.yaml"):
        f = root / name
        if f.exists():
            data = _deep_merge(data, yaml.safe_load(f.read_text()) or {})
    return Config(data, root)


@lru_cache(maxsize=1)
def get_config() -> Config:
    return load_config()
