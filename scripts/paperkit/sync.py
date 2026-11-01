"""Keep the paper bib equal to the set of cited keys.

Offline and fast, so the PostToolUse hook can run it after every .tex edit:
- cited key in archive.bib     -> moved into the paper bib
- paper bib entry not cited    -> moved to archive.bib
- cited key in neither         -> reported as unknown
- cited key not `read-full`    -> reported as unread
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from . import bib, config, literature, tex

ARCHIVE_HEADER = """% archive.bib, managed by the acl-paper plugin.
% Entries that were fetched or once cited but are not cited right now.
% The bib sync moves an entry into the paper bib as soon as it is cited,
% and back here once the last citation is gone. Do not edit by hand.

"""


@dataclass
class SyncResult:
    moved_in: list[str] = field(default_factory=list)
    moved_out: list[str] = field(default_factory=list)
    unknown: dict[str, list[str]] = field(default_factory=dict)
    unread: list[str] = field(default_factory=list)
    nocite_all: bool = False

    @property
    def changed(self) -> bool:
        return bool(self.moved_in or self.moved_out)

    def messages(self) -> list[str]:
        out = []
        if self.moved_in:
            out.append("Bib sync: added to paper bib: " + ", ".join(self.moved_in))
        if self.moved_out:
            out.append("Bib sync: moved to archive (no longer cited): " + ", ".join(self.moved_out))
        for key, where in self.unknown.items():
            out.append(
                f"⚠️ Cited key `{key}` ({', '.join(where[:3])}) has no BibTeX entry. "
                "Fetch it through a source skill (acl-anthology, arxiv, project sources) "
                "or ask the user to paste the authoritative entry. Never write it by hand."
            )
        if self.unread:
            out.append(
                "⚠️ Cited but not read in full (status != read-full): "
                + ", ".join(self.unread)
                + ". Read the body of each paper and fill its notes before relying on the citation."
            )
        if self.nocite_all:
            out.append("Note: \\nocite{*} is present, so uncited entries are not archived.")
        return out


def _crossrefs(entries: dict[str, bib.Entry], keys: set[str]) -> set[str]:
    out = set(keys)
    for key in keys:
        if key in entries:
            ref = entries[key].field("crossref")
            if ref:
                out.add(ref)
    return out


def run(root: Path, cfg: dict) -> SyncResult:
    main = root / cfg["main_tex"]
    lit = config.lit_dir(root, cfg)
    paper_path = config.paper_bib(root, cfg)
    archive_path = config.archive_bib(root, cfg)

    files = tex.all_tex_files(root, main, exclude=lit)
    cites, nocite_all = tex.citations(files)
    res = SyncResult(nocite_all=nocite_all)

    paper = bib.read(paper_path)
    archive = bib.read(archive_path) or [ARCHIVE_HEADER]
    p_entries, a_entries = bib.entries(paper), bib.entries(archive)
    wanted = _crossrefs({**a_entries, **p_entries}, set(cites))

    if not nocite_all:
        for key in list(p_entries):
            if key not in wanted:
                entry = bib.remove(paper, key)
                bib.remove(archive, key)
                bib.append(archive, entry)
                res.moved_out.append(key)

    for key in sorted(wanted):
        if key in p_entries:
            continue
        if key in a_entries:
            bib.append(paper, bib.remove(archive, key))
            res.moved_in.append(key)
        elif key in cites:
            res.unknown[key] = [
                f"{p.relative_to(root.resolve()) if p.is_relative_to(root.resolve()) else p}:{n}"
                for p, n in cites[key]
            ]

    if res.changed:
        bib.write(paper_path, paper)
        bib.write(archive_path, archive)

    for key in sorted(cites):
        if key not in res.unknown and literature.status(root, cfg, key) != literature.STATUS_READ:
            res.unread.append(key)

    if (lit / "notes").is_dir():
        literature.build_index(root, cfg, set(cites))
    return res
