"""The `literature/` folder: PDFs, Markdown text, reading notes and the index.

Layout (all file names are the cite key with `/` and `:` replaced by `_`):

    literature/pdf/<key>.pdf     the paper
    literature/md/<key>.md       `pdftotext -layout` of the PDF
    literature/notes/<key>.md    reading notes; frontmatter carries the status
    literature/index.md          generated overview, never edited by hand
    literature/archive.bib       entries that are not cited right now
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

from . import bib, config

STATUS_FETCHED = "fetched"
STATUS_READ = "read-full"

NOTES_TEMPLATE = """---
key: {key}
title: {title}
source: {source}
id: {id}
status: {status}
---

## Read

<!-- Which parts you read, e.g. "full paper" or "Sec. 1-5, Tab. 2-3, App. B". -->

## Claims this paper supports

<!-- One line per claim, each with its location in the body (never the abstract):
- <claim in your words> (Sec. 4.2, p. 6): "<short quote>"
-->

## Relevance to our paper

<!-- Where and why we would cite it, or why not. -->
"""


def safe_name(key: str) -> str:
    return key.replace("/", "_").replace(":", "_")


def paths(root: Path, cfg: dict, key: str) -> dict[str, Path]:
    lit = config.lit_dir(root, cfg)
    name = safe_name(key)
    return {
        "pdf": lit / "pdf" / f"{name}.pdf",
        "md": lit / "md" / f"{name}.md",
        "notes": lit / "notes" / f"{name}.md",
    }


def ensure_layout(root: Path, cfg: dict) -> None:
    lit = config.lit_dir(root, cfg)
    for sub in ("pdf", "md", "notes"):
        (lit / sub).mkdir(parents=True, exist_ok=True)


def pdftotext_available() -> bool:
    return shutil.which("pdftotext") is not None


def convert(pdf: Path, md: Path) -> None:
    if not pdftotext_available():
        raise RuntimeError(
            "pdftotext is not installed (macOS: `brew install poppler`, "
            "Debian/Ubuntu: `sudo apt install poppler-utils`)."
        )
    subprocess.run(["pdftotext", "-layout", str(pdf), str(md)], check=True)


def is_pdf(path: Path) -> bool:
    with path.open("rb") as fh:
        return fh.read(5) == b"%PDF-"


# --- notes -----------------------------------------------------------------

_FM = re.compile(r"\A---\n(.*?)\n---\n", re.S)


def read_frontmatter(path: Path) -> dict[str, str]:
    m = _FM.match(path.read_text(encoding="utf-8"))
    if not m:
        return {}
    out = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            out[k.strip()] = v.strip()
    return out


def set_frontmatter(path: Path, key: str, value: str) -> None:
    text = path.read_text(encoding="utf-8")
    m = _FM.match(text)
    lines = m.group(1).splitlines()
    for i, line in enumerate(lines):
        if line.split(":", 1)[0].strip() == key:
            lines[i] = f"{key}: {value}"
            break
    else:
        lines.append(f"{key}: {value}")
    path.write_text("---\n" + "\n".join(lines) + "\n---\n" + text[m.end():], encoding="utf-8")


def create_notes(root: Path, cfg: dict, key: str, title: str, source: str, ident: str) -> Path:
    p = paths(root, cfg, key)["notes"]
    if not p.exists():
        p.write_text(
            NOTES_TEMPLATE.format(
                key=key, title=title.replace("\n", " "), source=source, id=ident,
                status=STATUS_FETCHED,
            ),
            encoding="utf-8",
        )
    return p


def _section(text: str, heading: str) -> str:
    m = re.search(rf"^## {re.escape(heading)}\s*$(.*?)(?=^## |\Z)", text, re.M | re.S)
    body = m.group(1) if m else ""
    return re.sub(r"<!--.*?-->", "", body, flags=re.S).strip()


def mark_read(root: Path, cfg: dict, key: str) -> list[str]:
    """Set status read-full. Returns the problems that block it (empty = done)."""
    p = paths(root, cfg, key)
    problems = []
    if not p["notes"].exists():
        return [f"No notes file for `{key}`. Add the paper through a source first."]
    if not p["md"].exists():
        problems.append(f"{p['md']} is missing, so the full text cannot have been read.")
    text = p["notes"].read_text(encoding="utf-8")
    if not _section(text, "Read"):
        problems.append("`## Read` is empty: say which parts of the paper you read.")
    claims = _section(text, "Claims this paper supports")
    if not re.search(r"^\s*-\s+\S", claims, re.M):
        problems.append(
            "`## Claims this paper supports` has no claim line with a body location."
        )
    if not problems:
        set_frontmatter(p["notes"], "status", STATUS_READ)
    return problems


def status(root: Path, cfg: dict, key: str) -> str | None:
    p = paths(root, cfg, key)["notes"]
    return read_frontmatter(p).get("status") if p.exists() else None


def known_ids(root: Path, cfg: dict) -> dict[tuple[str, str], str]:
    """(source, id) -> key for every paper that already has notes."""
    out = {}
    notes_dir = config.lit_dir(root, cfg) / "notes"
    if notes_dir.is_dir():
        for p in notes_dir.glob("*.md"):
            fm = read_frontmatter(p)
            if fm.get("source") and fm.get("id"):
                out[(fm["source"], fm["id"])] = fm.get("key", p.stem)
    return out


# --- index -----------------------------------------------------------------

def build_index(root: Path, cfg: dict, cited: set[str]) -> Path:
    lit = config.lit_dir(root, cfg)
    rows = []
    for p in sorted((lit / "notes").glob("*.md")):
        fm = read_frontmatter(p)
        key = fm.get("key", p.stem)
        has_pdf = paths(root, cfg, key)["pdf"].exists()
        rows.append(
            "| `{}` | {} | {} | {} | {} | {} |".format(
                key,
                fm.get("title", "").replace("|", "\\|"),
                fm.get("source", ""),
                "✅ read-full" if fm.get("status") == STATUS_READ else "📄 fetched",
                "yes" if key in cited else "",
                "" if has_pdf else "⚠️ missing",
            )
        )
    out = lit / "index.md"
    out.write_text(
        "# Literature index\n\n"
        "Generated by `paperkit.py index` (also on every bib sync). Do not edit by hand:\n"
        "the status comes from `notes/<key>.md`.\n\n"
        "| Key | Title | Source | Status | Cited | PDF |\n"
        "|---|---|---|---|---|---|\n" + "\n".join(rows) + "\n",
        encoding="utf-8",
    )
    return out


def titles(root: Path, cfg: dict) -> dict[str, str]:
    """normalised title -> key across both bib files, for duplicate detection."""
    out = {}
    for path in (config.paper_bib(root, cfg), config.archive_bib(root, cfg)):
        for key, e in bib.entries(bib.read(path)).items():
            t = bib.normalize_title(e.field("title"))
            if t:
                out[t] = key
    return out
