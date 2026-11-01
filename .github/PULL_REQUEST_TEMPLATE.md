## What and why

<!-- Which skill or script, and the problem this solves. Link the issue: Closes #... -->

## Checklist

- [ ] `pytest` passes (and `pytest --network` if sources or guideline URLs changed)
- [ ] Version bumped in `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `scripts/paperkit/__init__.py` and `pyproject.toml`, if this is a release
- [ ] `CHANGELOG.md` updated under `## [Unreleased]`
- [ ] No ARR/ACL/ACLPUB guideline text copied into the repo (only URLs in `guideline_sources.json`)
- [ ] Skills still say how the user stays the author (no silent rewriting, no generated BibTeX)
- [ ] Tested in a real paper project with `/plugin marketplace add ./` (describe below)

## How it was tested
