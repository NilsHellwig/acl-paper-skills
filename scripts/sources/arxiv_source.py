"""arXiv adapter: search via the `arxiv` package, BibTeX from arxiv.org/bibtex."""

from __future__ import annotations

import re
import time
import urllib.request
from pathlib import Path

NAME = "arxiv"
REQUIRES = ["arxiv"]

USER_AGENT = "acl-paper-plugin (https://github.com/NilsHellwig/acl-paper-skills)"
_ID = re.compile(r"(\d{4}\.\d{4,5}|[a-z-]+(?:\.[A-Z]{2})?/\d{7})(v\d+)?")


def _client():
    import arxiv

    # arXiv asks for at most one request every three seconds.
    return arxiv.Client(page_size=50, delay_seconds=3, num_retries=3)


def normalize_id(ident: str) -> str:
    """Accept bare ids, versioned ids and abs/pdf URLs; return the bare id."""
    m = _ID.search(ident)
    if not m:
        raise LookupError(f"`{ident}` is not an arXiv identifier.")
    return m.group(1)


def search(query: str, limit: int = 10, year_from: int | None = None,
           year_to: int | None = None) -> list[dict]:
    import arxiv

    # Plain words search all fields; arXiv syntax (ti:, au:, abs:, AND) passes through.
    search = arxiv.Search(
        query=query, max_results=limit * 3 if (year_from or year_to) else limit,
        sort_by=arxiv.SortCriterion.Relevance,
    )
    hits = []
    for r in _client().results(search):
        year = r.published.year
        if (year_from and year < year_from) or (year_to and year > year_to):
            continue
        hits.append({
            "id": normalize_id(r.entry_id),
            "title": r.title,
            "authors": [a.name for a in r.authors],
            "year": year,
            "venue": f"arXiv ({r.primary_category})" + (f"; {r.journal_ref}" if r.journal_ref else ""),
            "url": r.entry_id,
            "abstract": r.summary,
        })
        if len(hits) >= limit:
            break
    return hits


def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def fetch_pdf(ident: str, dest: Path) -> None:
    dest.write_bytes(_get(f"https://arxiv.org/pdf/{normalize_id(ident)}"))
    time.sleep(3)


def bibtex(ident: str) -> str:
    text = _get(f"https://arxiv.org/bibtex/{normalize_id(ident)}").decode("utf-8")
    if not text.lstrip().startswith("@"):
        raise LookupError(f"arXiv returned no BibTeX for `{ident}`.")
    return text.strip()
