"""<SOURCE NAME> adapter for the acl-paper plugin.

Contract (checked by `paperkit.py test-source`):
- search() returns dicts with id, title, authors, year, venue, url (+ optional abstract)
- fetch_pdf() writes a real PDF to `dest`
- bibtex() returns the source's own entry; never assemble BibTeX from metadata
"""

from __future__ import annotations

import urllib.request
from pathlib import Path

NAME = "<source-name>"
REQUIRES: list[str] = []  # pip names of third-party packages imported below

USER_AGENT = "acl-paper-plugin (https://github.com/NilsHellwig/nlp-paper-assistant)"


def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def search(query: str, limit: int = 10, year_from: int | None = None,
           year_to: int | None = None) -> list[dict]:
    raise NotImplementedError


def fetch_pdf(ident: str, dest: Path) -> None:
    raise NotImplementedError


def bibtex(ident: str) -> str:
    raise NotImplementedError
