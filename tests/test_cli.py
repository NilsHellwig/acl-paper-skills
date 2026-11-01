"""End-to-end through paperkit.py and the hook, with an offline fake source."""

import json
import subprocess
import sys

from conftest import ROOT
from paperkit import bib, config, literature

PK = [sys.executable, str(ROOT / "scripts" / "paperkit.py")]
HOOK = [sys.executable, str(ROOT / "scripts" / "hook_bibsync.py")]

FAKE_ADAPTER = '''
from pathlib import Path
NAME = "fake"
REQUIRES = []
def search(query, limit=10, year_from=None, year_to=None):
    return [{"id": "F1", "title": "Fake Paper", "authors": ["A B"], "year": 2024,
             "venue": "Fake", "url": "https://example.org/F1"}]
def fetch_pdf(ident, dest):
    Path(dest).write_bytes(b"%PDF-1.4\\n%fake\\n")
def bibtex(ident):
    return "@article{jones2021,\\n  title = {Fake Paper},\\n  year = {2021}\\n}"
'''


def run(args, cwd, stdin=None):
    return subprocess.run(PK + args, cwd=cwd, input=stdin, capture_output=True, text=True)


def with_fake_source(root, cfg, monkeypatch):
    adapter = root / ".claude" / "skills" / "fake-source" / "adapter.py"
    adapter.parent.mkdir(parents=True)
    adapter.write_text(FAKE_ADAPTER)
    cfg["sources"] = {**cfg["sources"], "fake": ".claude/skills/fake-source/adapter.py"}
    config.save(root, cfg)
    # The fake PDF is not convertible; stand in for pdftotext.
    monkeypatch.setenv("PATH", str(root / "bin") + ":" + __import__("os").environ["PATH"])
    (root / "bin").mkdir()
    stub = root / "bin" / "pdftotext"
    stub.write_text('#!/bin/sh\necho "converted text" > "$3"\n')
    stub.chmod(0o755)


def test_init_writes_config_and_layout(tmp_path):
    (tmp_path / "main.tex").write_text("\\documentclass{article}\\usepackage[review]{acl}\n\\bibliography{refs}\n")
    r = subprocess.run(PK + ["init", "--python", sys.executable, "--main-tex", "main.tex"],
                       cwd=tmp_path, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    cfg = json.loads((tmp_path / "paper.config.json").read_text())
    assert cfg["bib"] == "refs.bib" and cfg["main_tex"] == "main.tex"
    for p in ("literature/pdf", "literature/md", "literature/notes", "literature/archive.bib",
              "literature/index.md", "report.md", "refs.bib"):
        assert (tmp_path / p).exists(), p


def test_add_through_project_source_then_cite(project, monkeypatch):
    root, cfg = project
    with_fake_source(root, cfg, monkeypatch)
    r = run(["test-source", "fake", "fake", "F1"], root)
    assert r.returncode == 0 and r.stdout.count("✅") == 3, r.stdout + r.stderr

    r = run(["add", "fake", "F1"], root)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert out["key"] == "jones2021"
    # jones2021 is already cited in the fixture, so the add's sync moves it in at once.
    assert "jones2021" in bib.entries(bib.read(root / "custom.bib"))
    assert literature.status(root, cfg, "jones2021") == "fetched"

    r = run(["add", "fake", "F1"], root)
    assert "Already in library" in r.stderr

    r = run(["search", "fake", "anything"], root)
    assert "already in library as `jones2021`" in r.stdout


def test_bib_paste_and_duplicate_title(project):
    root, _ = project
    r = run(["bib-paste"], root, stdin="@misc{new1,\n title={Brand New}\n}")
    assert r.returncode == 0 and "added to archive.bib" in r.stdout
    r = run(["bib-paste"], root, stdin="@misc{new2,\n title={Brand {N}ew}\n}")
    assert r.returncode == 2 and "new1" in r.stderr


def test_add_local_requires_entry(project, tmp_path):
    root, _ = project
    pdf = tmp_path / "x.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    r = run(["add-local", str(pdf), "--key", "nope"], root)
    assert r.returncode == 2 and "bib-paste" in r.stderr


def test_hook_reports_and_ignores(project):
    root, _ = project
    payload = {"tool_input": {"file_path": str(root / "acl_latex.tex")}}
    r = subprocess.run(HOOK, input=json.dumps(payload), capture_output=True, text=True)
    ctx = json.loads(r.stdout)["hookSpecificOutput"]["additionalContext"]
    assert "Aho:72" in ctx and "jones2021" in ctx

    payload = {"tool_input": {"file_path": str(root / "notes.txt")}}
    r = subprocess.run(HOOK, input=json.dumps(payload), capture_output=True, text=True)
    assert r.stdout == "" and r.returncode == 0


def test_hook_silent_outside_projects(tmp_path):
    (tmp_path / "a.tex").write_text("x")
    payload = {"tool_input": {"file_path": str(tmp_path / "a.tex")}}
    r = subprocess.run(HOOK, input=json.dumps(payload), capture_output=True, text=True)
    assert r.stdout == "" and r.returncode == 0


def test_commands_without_project_fail_clearly(tmp_path):
    r = run(["sync"], tmp_path)
    assert r.returncode == 1 and "/acl-paper:init" in r.stderr


def test_init_gitignore_modes(tmp_path):
    (tmp_path / "main.tex").write_text("\\documentclass{article}\\usepackage{acl}\n\\bibliography{refs}\n")
    (tmp_path / ".gitignore").write_text("*.aux")
    args = PK + ["init", "--python", sys.executable, "--main-tex", "main.tex"]
    subprocess.run(args + ["--gitignore", "files"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(args + ["--gitignore", "files"], cwd=tmp_path, check=True, capture_output=True)
    text = (tmp_path / ".gitignore").read_text()
    assert text.startswith("*.aux\n")
    assert text.count("# acl-paper: literature") == 1
    assert "/literature/pdf/" in text and "/literature/md/" in text and "/literature/\n" not in text

    other = tmp_path / "other"
    other.mkdir()
    (other / "main.tex").write_text((tmp_path / "main.tex").read_text())
    subprocess.run(args + ["--gitignore", "all"], cwd=other, check=True, capture_output=True)
    assert (other / ".gitignore").read_text() == "# acl-paper: literature\n/literature/\n"
    subprocess.run(args, cwd=tmp_path / "other", check=True, capture_output=True)
