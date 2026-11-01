import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "paper"


def pytest_addoption(parser):
    parser.addoption("--network", action="store_true", help="run tests that hit arXiv / GitHub")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--network"):
        return
    skip = pytest.mark.skip(reason="needs --network")
    for item in items:
        if "network" in item.keywords:
            item.add_marker(skip)


@pytest.fixture
def project(tmp_path, monkeypatch):
    """A copy of the fixture paper, initialised like /acl-paper:init would."""
    from paperkit import config, literature, sync

    dest = tmp_path / "paper"
    shutil.copytree(FIXTURE, dest)
    cfg = {**config.DEFAULTS, "python": sys.executable, "main_tex": "acl_latex.tex",
           "bib": "custom.bib"}
    config.save(dest, cfg)
    literature.ensure_layout(dest, cfg)
    config.archive_bib(dest, cfg).write_text(sync.ARCHIVE_HEADER, encoding="utf-8")
    monkeypatch.chdir(dest)
    return dest, config.load(dest)
