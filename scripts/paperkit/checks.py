"""Cheap deterministic checks that back up the LLM pass of /acl-paper:proofread.

Each finding carries a suggested severity and report category. Findings are
candidates: the proofread skill confirms each one in context before it goes
into report.md.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from . import literature, tex

DATA = Path(__file__).resolve().parent / "data"


@dataclass
class Finding:
    check: str
    severity: str  # high | medium | low
    category: str
    file: str
    line: int
    text: str
    hint: str


# Arguments that are labels or code, never prose.
_NON_PROSE_ARG = re.compile(
    r"\\(?:[A-Za-z]*cite[A-Za-z]*|ref|cref|Cref|autoref|eqref|pageref|label|url|href|"
    r"input|include|usepackage|documentclass|begin|end|bibliography|bibliographystyle|"
    r"includegraphics|newcommand|renewcommand|definecolor)\*?\s*(?:\[[^\]]*\])*\s*\{[^}]*\}"
)
_INLINE_MATH = re.compile(r"\$[^$]*\$|\\\([^)]*\\\)")
_COMMAND = re.compile(r"\\[A-Za-z]+\*?")


def prose(line: str) -> str:
    return _COMMAND.sub(" ", _INLINE_MATH.sub(" ", _NON_PROSE_ARG.sub(" ", line)))


def _body_lines(files: list[Path]) -> list[tuple[Path, int, str]]:
    """All lines in reading order, minus the main file's preamble."""
    out = []
    for i, path in enumerate(files):
        lines = list(tex.iter_lines(path))
        if i == 0:
            start = next((k for k, (_, l) in enumerate(lines) if "\\begin{document}" in l), -1)
            lines = lines[start + 1:]
        out += [(path, n, l) for n, l in lines]
    return out


def _words(name: str) -> list[str]:
    return [
        l.strip() for l in (DATA / name).read_text(encoding="utf-8").splitlines()
        if l.strip() and not l.startswith("#")
    ]


def _rel(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root.resolve()))
    except ValueError:
        return str(path)


def run(root: Path, cfg: dict, only: list[Path] | None = None) -> list[Finding]:
    main = root / cfg["main_tex"]
    files = tex.ordered_files(root, main)
    lines = _body_lines(files)
    scope = {p.resolve() for p in only} if only else None

    def keep(path: Path) -> bool:
        return scope is None or path in scope

    out: list[Finding] = []
    add = lambda *a: out.append(Finding(*a))  # noqa: E731

    ai_words = _words("ai_vocabulary.txt")
    ai_re = re.compile(r"\b(" + "|".join(re.escape(w) for w in ai_words) + r")\b", re.I)
    pairs = [l.split("\t") for l in _words("spelling_variants.txt")]
    wrong = {uk if cfg["english"] == "us" else us: us if cfg["english"] == "us" else uk
             for us, uk in pairs}
    wrong_re = re.compile(r"\b(" + "|".join(map(re.escape, wrong)) + r")\b", re.I)

    checks = [
        ("leftover-marker", "high", "Content", re.compile(r"\bTODO\b|\bFIXME\b|\bXXX\b|\\todo\b"),
         "Leftover marker. Resolve or remove before submission."),
        ("duplicate-word", "medium", "Language", re.compile(r"\b(\w+)\s+\1\b", re.I),
         "Repeated word."),
        ("plain-text-citation", "medium", "Citations",
         re.compile(r"\b[A-Z][a-z][A-Za-z'-]*(?: et al\.?| and [A-Z][a-z][A-Za-z'-]*)?"
                    r"(?: \((?:19|20)\d{2}[a-z]?\)|, (?:19|20)\d{2}[a-z]?\b)"),
         "Author-year written as plain text. Cite with \\citet{} / \\citep{}."),
        ("em-dash", "low", "AI-Style", re.compile(r"---|—"),
         "Em dash. Frequent em dashes read as machine-written: prefer a comma, parentheses or a new sentence."),
        ("straight-quote", "low", "Language", re.compile(r"(?:^|[\s(])\"\w"),
         "Straight double quote. Use ``...'' in LaTeX."),
        ("ref-without-tilde", "low", "Consistency",
         re.compile(r"[A-Za-z.]\s+\\(?:ref|cref|Cref|autoref|eqref)\{"),
         "Use a non-breaking space before \\ref (e.g. Table~\\ref{...})."),
    ]

    for path, no, raw in lines:
        if not keep(path):
            continue
        text = prose(raw)
        rel = _rel(root, path)
        for name, sev, cat, rx, hint in checks:
            src = raw if name in ("leftover-marker", "ref-without-tilde") else text
            if name == "plain-text-citation":
                src = re.sub(r"\\[A-Za-z]*cite[A-Za-z]*\*?(\[[^\]]*\])*\{[^}]*\}", " ", raw)
            for m in rx.finditer(src):
                if name == "duplicate-word" and m.group(1).isdigit():
                    continue
                add(name, sev, cat, rel, no, m.group(0).strip(), hint)
        for m in ai_re.finditer(text):
            add("ai-vocabulary", "low", "AI-Style", rel, no, m.group(0),
                "Overused LLM word. Check whether a plainer word says the same.")
        for m in wrong_re.finditer(text):
            target = wrong[m.group(0).lower()]
            add("spelling-variant", "low", "Language", rel, no, m.group(0),
                f"Paper uses {cfg['english'].upper()} English: `{target}`.")

    out += _abbreviations(root, cfg, lines, keep)
    out += _unread_citations(root, cfg, files, keep)

    full = "\n".join(l for _, _, l in lines)
    if not re.search(r"\\section\*?\{\s*Limitations\s*\}", full):
        add("missing-limitations", "high", "ACL-Compliance", _rel(root, main), 1, "",
            "No Limitations section. ARR has required one; confirm the current rule with guidelines-check.")
    return out


_ABBR = re.compile(r"\b([A-Z][A-Z0-9-]*[A-Z0-9])s?\b")


def _abbreviations(root, cfg, lines, keep) -> list[Finding]:
    allow = set(cfg.get("abbreviation_allowlist", [])) | {"TODO", "FIXME", "XXX"}
    first_use: dict[str, tuple[Path, int, int]] = {}
    intro: dict[str, int] = {}
    for idx, (path, no, raw) in enumerate(lines):
        text = prose(raw)
        for m in re.finditer(r"\(\s*([A-Z][A-Z0-9-]*[A-Z0-9])s?\s*[;,)]", text):
            intro.setdefault(m.group(1), idx)
        for m in _ABBR.finditer(text):
            tok = m.group(1)
            if tok in allow or sum(c.isupper() for c in tok) < 2:
                continue
            first_use.setdefault(tok, (path, no, idx))
    out = []
    for tok, (path, no, idx) in first_use.items():
        if not keep(path):
            continue
        if tok not in intro:
            hint = "Abbreviation never introduced with its spelled-out form."
        elif intro[tok] > idx:
            hint = "Abbreviation used before its spelled-out introduction."
        else:
            continue
        out.append(Finding("abbreviation", "low", "Consistency", _rel(root, path), no, tok,
                           hint + " Names of methods, models and datasets usually need none."))
    return out


def _unread_citations(root, cfg, files, keep) -> list[Finding]:
    cites, _ = tex.citations(files)
    out = []
    for key, where in sorted(cites.items()):
        status = literature.status(root, cfg, key)
        if status == literature.STATUS_READ:
            continue
        path, no = where[0]
        if not keep(path):
            continue
        hint = ("No reading notes: the paper was never added through a source."
                if status is None else "Paper was fetched but not read in full.")
        out.append(Finding("cited-unread", "high", "Citations", _rel(root, path), no, key,
                           hint + " Verify the claim against the paper body."))
    return out
