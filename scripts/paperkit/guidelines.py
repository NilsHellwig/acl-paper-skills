"""Fetch ARR / ACL / ACLPUB documents fresh from GitHub into a temp folder."""

from __future__ import annotations

import json
import tempfile
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

SOURCES = Path(__file__).resolve().parent / "data" / "guideline_sources.json"
USER_AGENT = "acl-paper-plugin (https://github.com/NilsHellwig/acl-paper-skills)"


def catalog() -> dict:
    return json.loads(SOURCES.read_text(encoding="utf-8"))


def fetch(names: list[str], out: Path | None = None) -> tuple[dict[str, Path], dict[str, str]]:
    """Download documents or sets. Returns (fetched paths, failures name -> reason)."""
    cat = catalog()
    docs: list[str] = []
    for name in names:
        docs += cat["sets"].get(name, [name])
    out = out or Path(tempfile.mkdtemp(prefix="acl-paper-guidelines-"))
    out.mkdir(parents=True, exist_ok=True)
    fetched, failed = {}, {}
    for doc in dict.fromkeys(docs):
        url = cat["documents"].get(doc)
        if url is None:
            failed[doc] = "unknown document or set name"
            continue
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = resp.read().decode("utf-8")
        except (urllib.error.URLError, TimeoutError) as exc:
            failed[doc] = f"{url}: {exc}"
            continue
        path = out / f"{doc}.md"
        path.write_text(
            f"<!-- fetched {date.today().isoformat()} from {url} -->\n\n{body}",
            encoding="utf-8",
        )
        fetched[doc] = path
    return fetched, failed
