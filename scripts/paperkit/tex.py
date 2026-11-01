"""Reading the paper's LaTeX sources: file order, comments, citations."""

from __future__ import annotations

import re
from pathlib import Path

CITE_RE = re.compile(
    r"\\[A-Za-z]*cite[A-Za-z]*\*?\s*(?:\[[^\]]*\]\s*){0,2}\{([^}]*)\}"
)
INPUT_RE = re.compile(r"\\(?:input|include|subfile)\s*\{([^}]+)\}")
BIBLIOGRAPHY_RE = re.compile(r"\\bibliography\s*\{([^}]+)\}")
ACL_PACKAGE_RE = re.compile(r"\\usepackage\s*(?:\[([^\]]*)\])?\s*\{acl\}")


def strip_comment(line: str) -> str:
    """Drop everything from the first unescaped `%`."""
    m = re.search(r"(?<!\\)%", line)
    return line[:m.start()] if m else line


def find_main_tex(root: Path) -> list[Path]:
    """Candidate main files: a \\documentclass plus the acl package."""
    hits = []
    for p in sorted(root.rglob("*.tex")):
        if any(part.startswith(".") for part in p.relative_to(root).parts):
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        if "\\documentclass" in text and ACL_PACKAGE_RE.search(text):
            hits.append(p)
    return hits


def acl_mode(main: Path) -> str | None:
    """`review`, `final` or `preprint` from \\usepackage[...]{acl}."""
    m = ACL_PACKAGE_RE.search(main.read_text(encoding="utf-8", errors="replace"))
    if not m:
        return None
    opts = [o.strip() for o in (m.group(1) or "").split(",")]
    for mode in ("review", "final", "preprint"):
        if mode in opts:
            return mode
    return "final"


def bib_names(main: Path) -> list[str]:
    text = "\n".join(
        strip_comment(l)
        for l in main.read_text(encoding="utf-8", errors="replace").splitlines()
    )
    names = []
    for m in BIBLIOGRAPHY_RE.finditer(text):
        names += [n.strip() for n in m.group(1).split(",") if n.strip()]
    return names


def ordered_files(root: Path, main: Path) -> list[Path]:
    """Main file followed by everything it pulls in, in reading order."""
    seen: list[Path] = []

    def visit(path: Path) -> None:
        if path in seen or not path.is_file():
            return
        seen.append(path)
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            for m in INPUT_RE.finditer(strip_comment(line)):
                target = (root / m.group(1).strip())
                if target.suffix != ".tex":
                    target = target.with_name(target.name + ".tex")
                visit(target.resolve())

    visit(main.resolve())
    return seen


def all_tex_files(root: Path, main: Path, exclude: Path) -> list[Path]:
    """Files reached from main first, then any other .tex in the project."""
    files = ordered_files(root, main)
    exclude = exclude.resolve()
    for p in sorted(root.rglob("*.tex")):
        rp = p.resolve()
        rel = p.relative_to(root).parts
        if rp in files or any(part.startswith(".") for part in rel):
            continue
        if exclude in rp.parents:
            continue
        files.append(rp)
    return files


def iter_lines(path: Path):
    """(line_number, line_without_comment) pairs."""
    for i, line in enumerate(
        path.read_text(encoding="utf-8", errors="replace").splitlines(), 1
    ):
        yield i, strip_comment(line)


def citations(files: list[Path]) -> tuple[dict[str, list[tuple[Path, int]]], bool]:
    """Map cite key -> locations, plus whether \\nocite{*} is present."""
    found: dict[str, list[tuple[Path, int]]] = {}
    nocite_all = False
    for path in files:
        # Whole-file matching so a \cite{a,\n b} split over lines still counts.
        text = "\n".join(line for _, line in iter_lines(path))
        for m in CITE_RE.finditer(text):
            no = text.count("\n", 0, m.start()) + 1
            for key in m.group(1).split(","):
                key = key.strip()
                if key == "*":
                    nocite_all = True
                elif key:
                    found.setdefault(key, []).append((path, no))
    return found, nocite_all
