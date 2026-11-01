# Contributing

Thanks for helping. Issues and pull requests are welcome; the issue forms ask for what a fix needs.

## Ground rules

- **Quality control first.** Skills help authors check and improve their own paper. Features that generate whole papers are out of scope.
- **No generated BibTeX.** Entries come from a source's own export or from the user.
- **No copied guidelines.** ARR, ACL and ACLPUB rules change every cycle. Add the document's URL to `scripts/paperkit/data/guideline_sources.json`; the skills fetch it at run time.
- **Stdlib only in `scripts/paperkit/`.** The hook runs it with any `python3`. Third-party imports belong in source adapters (`scripts/sources/`).

## Development

```bash
git clone https://github.com/NilsHellwig/nlp-paper-assistant
cd nlp-paper-assistant
uv venv && uv pip install -e ".[dev,sources]"   # or: python -m venv .venv && pip install -e ".[dev,sources]"
pytest                 # offline suite
pytest --network       # also checks upstream URLs and arXiv
```

Try the plugin from your checkout in a real paper project:

```
/plugin marketplace add /path/to/nlp-paper-assistant
/plugin install acl-paper@nlp-paper-assistant
```

Skills are written for agents: read `CLAUDE.md` in this repo before editing one.

## Releases

1. Move the `[Unreleased]` entries in `CHANGELOG.md` under a new version heading.
2. Bump the version in `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `scripts/paperkit/__init__.py` and `pyproject.toml` (`tests/test_repo.py` checks they agree).
3. Commit, tag `vX.Y.Z`, push the tag. The release workflow creates the GitHub release from the changelog.

Versioning follows SemVer: a change to the `paper.config.json` schema, the adapter contract or the `literature/` layout that breaks existing projects is a major bump.
