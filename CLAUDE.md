# CLAUDE.md

Development guide for the acl-paper plugin itself. (Paper projects get their own CLAUDE.md from `templates/CLAUDE.md`.)

## Layout

- `skills/<name>/SKILL.md`: one folder per skill. User-invoked skills set `disable-model-invocation: true`; `tests/test_repo.py` holds the list of which is which.
- `scripts/paperkit.py`: the CLI every skill calls as `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/paperkit.py`. `scripts/paperkit/`: its stdlib-only library.
- `scripts/sources/`: built-in source adapters (third-party imports allowed). The contract is the docstring of `scripts/paperkit/sources.py`.
- `hooks/hooks.json` → `scripts/hook_bibsync.py`: offline bib sync after `.tex`/`.bib` edits.
- `templates/`: files `init` copies into paper projects.

## Writing skills

- Skills are read by agents. Load the `writing-for-agents` skill (mattpocock-skills) before creating or editing one, if available.
- `${CLAUDE_PLUGIN_ROOT}` and `${CLAUDE_SKILL_DIR}` are substituted in SKILL.md only. Reference files and templates copied into projects must not rely on them.
- Upstream rules (ARR, ACL, ACLPUB) are fetched, never restated: a skill names the document set for `paperkit.py guidelines`, and states facts about the rules only as "check X in the fetched document".
- Skills that report on upstream rules or review issues tell the agent to cite identifier and document URL (printed by `paperkit.py guidelines`); URLs are never written into skills.
- Every rule lives in one place. Literature handling is in `skills/literature`, prose rules in `skills/writing`; other skills point there.

## Code

- Keep `scripts/paperkit/` free of third-party imports and compatible with Python 3.10.
- BibTeX stays raw text (`bib.Entry.raw`): never reformat an authoritative entry.
- Run `pytest` before committing; `pytest --network` when touching adapters or `guideline_sources.json`.
- Versions are bumped in four files at once (see CONTRIBUTING.md).
