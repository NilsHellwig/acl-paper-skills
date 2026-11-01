# CLAUDE.md

ACL paper project, set up with the acl-paper plugin (`/acl-paper:init`).

## Purpose

This setup is for quality control of a paper the authors write themselves: proofreading, checking citations against the sources, checking ARR guidelines, simulated reviews. Drafting text is possible on request, but the default role is reviewer and editor. When asked to edit, change the authors' text as little as needed and keep their voice.

Ask before assuming. Whenever the answer depends on something the project files do not settle (submission type, resubmission history, target venue, a formatting or wording choice with several valid options), put the question to the user with the AskUserQuestion tool, offering the plausible options with a recommendation, and continue once answered.

## Project

- Machine-readable settings (Python env, main `.tex`, bib file, English variant, key scheme, literature sources) live in `paper.config.json`. Read it from there.
- The plugin's script (`paperkit.py`) is reached through the acl-paper skills, which carry its path. Load the matching skill before searching, adding, reading or syncing literature.
- `report.md` collects review findings; `/acl-paper:proofread apply R12 R15` applies them.

## Literature rules

- Papers live in `literature/`: `pdf/<key>.pdf`, `md/<key>.md` (text via `pdftotext -layout`), `notes/<key>.md` (reading notes and status). `literature/index.md` is generated. Search and read the `.md`; open the PDF for figures, tables and page numbers.
- Judge a paper, and cite it, only after reading its body (introduction, method, results, tables). The abstract alone is never evidence for a claim. Record what you read and the claims with their body location in `notes/<key>.md`, then run `paperkit.py mark-read <key>`.
- BibTeX comes from an authoritative source only: a source skill (`acl-anthology`, `arxiv`, project sources under `.claude/skills/`) or an entry the user pastes (`paperkit.py bib-paste`). When neither exists, name the paper and ask the user for the entry.
- The paper bib holds exactly the cited entries. A hook moves entries between it and `literature/archive.bib` after every `.tex` edit. Leave both bib files to the scripts.
- Report only numbers that appear in the cited paper. Comparisons you compute yourself go in words, not as figures attributed to the paper.

## Style

<!-- Project-specific writing rules. They extend the plugin's `writing` skill and win where they differ. One rule per line, with the reason if it is not obvious. -->

## Terminology

<!-- Terms this paper defines or uses in a fixed sense, and their abbreviations. -->
