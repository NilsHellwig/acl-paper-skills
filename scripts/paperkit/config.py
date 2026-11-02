"""Locate and read `paper.config.json`, the machine-readable project config."""

from __future__ import annotations

import json
from pathlib import Path

CONFIG_NAME = "paper.config.json"

DEFAULTS = {
    "version": 1,
    "python": None,
    "main_tex": None,
    "bib": None,
    "english": "us",
    "venue": None,
    "paper_type": None,
    "stage": None,
    "key_scheme": "native",
    "literature_dir": "literature",
    "report": "report.md",
    "sources": {"acl-anthology": "builtin", "arxiv": "builtin"},
    "abbreviation_allowlist": [
        "ACL", "NLP", "AI", "API", "CPU", "GPU", "TPU", "ID", "PDF", "URL",
        "US", "UK", "EU", "USA", "II", "III", "IV", "VI", "OK",
    ],
}


VENUES = ("acl-arr", "semeval")
PAPER_TYPES = ("long", "short", "semeval-system", "semeval-task")
STAGES = ("review", "camera-ready")


class ConfigError(RuntimeError):
    pass


def find_root(start: Path | str | None = None) -> Path | None:
    """Walk up from `start` (default: cwd) to the directory holding the config."""
    here = Path(start or Path.cwd()).resolve()
    if here.is_file():
        here = here.parent
    for candidate in (here, *here.parents):
        if (candidate / CONFIG_NAME).is_file():
            return candidate
    return None


def require_root(start: Path | str | None = None) -> Path:
    root = find_root(start)
    if root is None:
        raise ConfigError(
            f"No {CONFIG_NAME} found. Run /acl-paper:init in the paper project first."
        )
    return root


def load(root: Path) -> dict:
    data = json.loads((root / CONFIG_NAME).read_text(encoding="utf-8"))
    return {**DEFAULTS, **data}


def save(root: Path, cfg: dict) -> None:
    (root / CONFIG_NAME).write_text(
        json.dumps(cfg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def lit_dir(root: Path, cfg: dict) -> Path:
    return root / cfg["literature_dir"]


def paper_bib(root: Path, cfg: dict) -> Path:
    if not cfg.get("bib"):
        raise ConfigError(f"`bib` is not set in {CONFIG_NAME}.")
    return root / cfg["bib"]


def archive_bib(root: Path, cfg: dict) -> Path:
    return lit_dir(root, cfg) / "archive.bib"
