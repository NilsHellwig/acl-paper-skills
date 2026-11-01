"""Repo consistency: versions, skills, referenced files."""

import json
import re

from conftest import ROOT

USER_INVOKED = {"init", "new-source", "proofread", "reviewer", "rebuttal", "camera-ready"}
MODEL_INVOKED = {"writing", "literature", "acl-anthology", "arxiv", "guidelines-check"}


def frontmatter(path):
    m = re.match(r"---\n(.*?)\n---\n", path.read_text(), re.S)
    assert m, f"{path} has no frontmatter"
    return dict(
        (k.strip(), v.strip()) for k, v in
        (line.split(":", 1) for line in m.group(1).splitlines() if ":" in line)
    )


def test_versions_match():
    plugin = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text())["version"]
    market = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text())["plugins"][0]["version"]
    from paperkit import __version__
    changelog = re.search(r"^## \[(\d+\.\d+\.\d+)\]", (ROOT / "CHANGELOG.md").read_text(), re.M).group(1)
    pyproject = re.search(r'^version = "(.+)"', (ROOT / "pyproject.toml").read_text(), re.M).group(1)
    assert plugin == market == __version__ == changelog == pyproject


def test_skill_set_and_invocation():
    skills = {p.parent.name: p for p in (ROOT / "skills").glob("*/SKILL.md")}
    assert set(skills) == USER_INVOKED | MODEL_INVOKED
    for name, path in skills.items():
        fm = frontmatter(path)
        assert fm["name"] == name
        assert fm.get("description")
        assert (fm.get("disable-model-invocation") == "true") == (name in USER_INVOKED), name


def test_plugin_paths_in_skills_exist():
    for path in (ROOT / "skills").glob("*/SKILL.md"):
        for ref in re.findall(r"\$\{CLAUDE_PLUGIN_ROOT\}/([\w./-]+)", path.read_text()):
            assert (ROOT / ref.rstrip(".")).exists(), f"{path}: {ref}"
        for ref in re.findall(r"\$\{CLAUDE_SKILL_DIR\}/([\w./-]+)", path.read_text()):
            assert (path.parent / ref).exists(), f"{path}: {ref}"


def test_guideline_sets_reference_known_documents():
    cat = json.loads((ROOT / "scripts" / "paperkit" / "data" / "guideline_sources.json").read_text())
    for name, docs in cat["sets"].items():
        assert set(docs) <= set(cat["documents"]), name
    skills = {p.parent.name for p in (ROOT / "skills").glob("*/SKILL.md")}
    assert set(cat["sets"]) <= skills
