"""Source adapters: one module per literature source.

Every adapter is a plain Python file defining:

    NAME: str                      # e.g. "arxiv"
    REQUIRES: list[str]            # pip package names the adapter imports
    def search(query: str, limit: int = 10, year_from: int | None = None,
               year_to: int | None = None) -> list[dict]
        # each hit: {"id", "title", "authors": [str], "year", "venue", "url"}
        # plus optional "abstract" (shown for triage only, never for judging a paper)
    def fetch_pdf(ident: str, dest: Path) -> None   # write the PDF to `dest`
    def bibtex(ident: str) -> str                   # authoritative entry, never generated

The core (`paperkit.py add`) does everything else: duplicate check, key
scheme, archive.bib, pdftotext, notes, index.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

BUILTIN_DIR = Path(__file__).resolve().parent.parent / "sources"
BUILTIN = {
    "acl-anthology": BUILTIN_DIR / "acl_anthology_source.py",
    "arxiv": BUILTIN_DIR / "arxiv_source.py",
}
REQUIRED = ("NAME", "REQUIRES", "search", "fetch_pdf", "bibtex")


class SourceError(RuntimeError):
    pass


def adapter_path(root: Path, cfg: dict, name: str) -> Path:
    spec = cfg.get("sources", {}).get(name)
    if spec is None:
        known = ", ".join(cfg.get("sources", {})) or "none"
        raise SourceError(f"Unknown source `{name}`. Configured sources: {known}.")
    return BUILTIN[name] if spec == "builtin" else (root / spec)


def load_path(path: Path) -> ModuleType:
    if not path.is_file():
        raise SourceError(f"Adapter file {path} does not exist.")
    spec = importlib.util.spec_from_file_location(f"paperkit_source_{path.stem}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    missing = [attr for attr in REQUIRED if not hasattr(module, attr)]
    if missing:
        raise SourceError(f"Adapter {path} is missing: {', '.join(missing)}.")
    return module


def load(root: Path, cfg: dict, name: str) -> ModuleType:
    return load_path(adapter_path(root, cfg, name))


def requirements(path: Path) -> list[str]:
    """REQUIRES without importing the adapter (its imports may be missing)."""
    import ast

    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "REQUIRES" for t in node.targets
        ):
            return list(ast.literal_eval(node.value))
    return []
