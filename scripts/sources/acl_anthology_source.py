"""ACL Anthology adapter, built on the `acl-anthology` package.

The Anthology metadata (~300 MB git clone) lives in one cache shared by all
projects. Searches load it offline; only `update_data()` pulls from GitHub.
"""

from __future__ import annotations

import os
import re
import urllib.request
import warnings
from pathlib import Path

NAME = "acl-anthology"
REQUIRES = ["acl-anthology", "typing_extensions"]

DATA_DIR = Path(
    os.environ.get("ACL_PAPER_ANTHOLOGY_DIR", Path.home() / ".cache" / "acl-paper" / "anthology")
)
USER_AGENT = "acl-paper-plugin (https://github.com/NilsHellwig/acl-paper-skills)"

_anthology = None


def _load():
    global _anthology
    if _anthology is None:
        warnings.filterwarnings("ignore")
        from acl_anthology import Anthology

        if (DATA_DIR / "data").is_dir():
            _anthology = Anthology(datadir=DATA_DIR / "data")
        else:
            _anthology = Anthology.from_repo(path=DATA_DIR, verbose=False)
    return _anthology


def update_data() -> None:
    """Clone or pull the Anthology metadata into the shared cache."""
    global _anthology
    from acl_anthology import Anthology

    _anthology = Anthology.from_repo(path=DATA_DIR, verbose=True)


def _paper(ident: str):
    a = _load()
    paper = a.get_paper(ident) or a.get_paper_by_bibkey(ident)
    if paper is None:
        raise LookupError(f"No ACL Anthology paper with id or bibkey `{ident}`.")
    return paper


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def search(query: str, limit: int = 10, year_from: int | None = None,
           year_to: int | None = None) -> list[dict]:
    """Rank papers by query-token overlap: title hits weigh 3, abstract hits 1."""
    terms = set(_tokens(query))
    phrase = " ".join(_tokens(query))
    scored = []
    for paper in _load().papers():
        year = int(paper.year)
        if (year_from and year < year_from) or (year_to and year > year_to):
            continue
        title = str(paper.title)
        t_tokens = set(_tokens(title))
        hits = terms & t_tokens
        if not hits and len(terms) > 1:
            a_tokens = set(_tokens(str(paper.abstract))) if paper.abstract else set()
            if len(terms & a_tokens) < max(2, len(terms) - 1):
                continue
        else:
            a_tokens = set(_tokens(str(paper.abstract))) if paper.abstract else set()
        score = 3 * len(hits) + len(terms & a_tokens)
        if phrase and phrase in " ".join(_tokens(title)):
            score += 5
        if score:
            scored.append((score, len(t_tokens), year, paper))
    # Ties: the tighter title match first, then the newer paper.
    scored.sort(key=lambda s: (-s[0], s[1], -s[2]))
    return [_hit(p) for *_, p in scored[:limit]]


def _hit(paper) -> dict:
    return {
        "id": paper.full_id,
        "key": paper.bibkey,
        "title": str(paper.title),
        "authors": [a.name.as_first_last() for a in paper.authors],
        "year": int(paper.year),
        "venue": ", ".join(paper.parent.venue_ids),
        "url": paper.web_url,
        "abstract": str(paper.abstract) if paper.abstract else "",
    }


def fetch_pdf(ident: str, dest: Path) -> None:
    paper = _paper(ident)
    if paper.pdf is None:
        raise LookupError(f"`{ident}` has no PDF in the ACL Anthology.")
    req = urllib.request.Request(paper.pdf.url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as resp:
        dest.write_bytes(resp.read())


def bibtex(ident: str) -> str:
    return _paper(ident).to_bibtex()
