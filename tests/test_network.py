"""Live checks against upstream. Run with `pytest --network` (weekly in CI)."""

import json
import urllib.request

import pytest

from conftest import ROOT

pytestmark = pytest.mark.network

CATALOG = json.loads((ROOT / "scripts" / "paperkit" / "data" / "guideline_sources.json").read_text())


@pytest.mark.parametrize("name,url", sorted(CATALOG["documents"].items()))
def test_guideline_document_still_exists(name, url):
    with urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=30) as r:
        assert r.status == 200, f"{name} moved: open a 'Guideline drift' issue"


def test_arxiv_bibtex_endpoint():
    pytest.importorskip("arxiv")
    from paperkit import sources
    adapter = sources.load_path(sources.BUILTIN["arxiv"])
    entry = adapter.bibtex("1706.03762")
    assert entry.startswith("@") and "Attention Is All You Need" in entry
