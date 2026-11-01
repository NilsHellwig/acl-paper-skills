# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.0] - 2026-11-01

### Added

- Skills: `init`, `writing`, `literature`, `acl-anthology`, `arxiv`, `new-source`, `proofread`, `guidelines-check`, `reviewer`, `rebuttal`, `camera-ready`.
- `paperkit.py`: stdlib-only core for the literature folder, lossless BibTeX handling, bib sync, reading notes with a `read-full` gate, deterministic proofreading checks and fresh fetching of ARR / ACL / ACLPUB documents.
- Source adapters for the ACL Anthology (`acl-anthology` package, shared metadata cache) and arXiv; adapter contract for project-local sources.
- PostToolUse hook that keeps the paper bib equal to the cited keys after every `.tex` edit.
- Tests, CI, weekly upstream drift check, issue and PR templates.

[Unreleased]: https://github.com/NilsHellwig/nlp-paper-assistant/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/NilsHellwig/nlp-paper-assistant/releases/tag/v0.1.0
