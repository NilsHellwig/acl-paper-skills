"""Comparing a previous PDF with the current LaTeX sources, for the revision notes.

The previous version is a PDF (`revision/previous.pdf`, text in
`revision/previous.txt`); the current one is the paper's `.tex` files. Both are
reduced to lowercase word and number tokens, aligned once with difflib, and the
result is reported per paragraph of the current sources. Citations, math, the
reference list and PDF artifacts (hyphenation, ligatures, line numbers) are
dropped or normalized, so what remains are changes in prose, numbers, tables
and figures. The tool classifies; judging what a change means is the caller's job.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path

from . import tex

MIN_CHUNK = 12          # removed text shorter than this many tokens is noise
MIN_PARAGRAPH = 3       # shorter paragraphs (headings, labels) are skipped
UNCHANGED = 0.98
NEW = 0.25
MOVED = 0.8
FLOATS = ("table", "table*", "figure", "figure*", "tabular", "tabularx")
SKIP_ENVS = ("equation", "equation*", "align", "align*", "eqnarray", "gather",
             "multline", "tikzpicture", "verbatim", "lstlisting", "algorithm",
             "algorithmic")
DROP_COMMANDS = ("cite", "citep", "citet", "citealp", "citeauthor", "citeyear",
                 "nocite", "ref", "eqref", "autoref", "cref", "Cref", "pageref",
                 "label", "url", "href", "includegraphics", "bibliography",
                 "bibliographystyle", "usepackage", "input", "include",
                 "vspace", "hspace", "setlength", "newcommand", "renewcommand",
                 "definecolor", "hypersetup")
SECTION_RE = re.compile(r"\\((?:sub)*section|paragraph)\*?\s*\{([^}]*)\}")
BEGIN_RE = re.compile(r"\\begin\s*\{([^}]+)\}")
END_RE = re.compile(r"\\end\s*\{([^}]+)\}")
DROP_RE = re.compile(
    r"\\(?:%s)\*?\s*(?:\[[^\]]*\]\s*)*(?:\{[^{}]*\})*" % "|".join(DROP_COMMANDS)
)
TOKEN_RE = re.compile(r"[a-z]{2,}|\d+(?:[.,]\d+)*")


@dataclass
class Paragraph:
    file: str
    line: int
    section: str
    float: bool
    tokens: list[str] = field(default_factory=list)


@dataclass
class Item:
    status: str          # changed | minor | new | removed | moved
    section: str
    where: str
    float: bool = False
    kept: float | None = None
    old: list[str] = field(default_factory=list)
    new: list[str] = field(default_factory=list)
    numbers: bool = False


def tokens(text: str) -> list[str]:
    return TOKEN_RE.findall(unicodedata.normalize("NFKC", text).lower())


# --- previous PDF text ---------------------------------------------------------

def old_tokens(text: str) -> list[str]:
    """Tokens of `pdftotext` output without the reference list."""
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
    lines = []
    in_refs = False
    for raw in text.splitlines():
        line = raw.strip()
        if re.fullmatch(r"References", line):
            in_refs = True
            continue
        if in_refs and re.match(r"(Appendix\b|[A-Z]\s+[A-Z][A-Za-z ]{3,60}$)", line):
            in_refs = False
        if in_refs or re.fullmatch(r"\d{3}", line):   # review-version line numbers
            continue
        lines.append(line)
    text = "\n".join(lines)
    text = re.sub(r"\((?:[^()]{0,100}?)\b(?:19|20)\d\d[a-z]?(?:[;,][^()]{0,100}?)?\)", " ", text)
    return tokens(text)


# --- current LaTeX -------------------------------------------------------------

def _prose(line: str) -> str:
    line = re.sub(r"\$[^$]*\$|\\\(.*?\\\)|\\\[.*?\\\]", " ", line)
    line = DROP_RE.sub(" ", line)
    line = re.sub(r"\\(?:begin|end)\s*\{[^}]*\}(?:\{[^}]*\})?", " ", line)
    line = re.sub(r"\\[A-Za-z]+\*?(?:\[[^\]]*\])*", " ", line)
    return re.sub(r"[{}&~\\]", " ", line)


def paragraphs(root: Path, main: Path) -> list[Paragraph]:
    """Paragraphs of the body in reading order, with section and float flag."""
    out: list[Paragraph] = []
    section = "Front matter"
    env_stack: list[str] = []
    skip_depth = 0
    in_body = False
    stop = False
    after_bib = False
    for path in tex.ordered_files(root, main):
        text = path.read_text(encoding="utf-8", errors="replace")
        in_body = in_body or "\\begin{document}" not in text
        buf: list[str] = []
        start = 0
        rel = str(path.relative_to(root)) if root in path.parents else path.name

        def flush() -> None:
            nonlocal buf, start
            toks = tokens(" ".join(buf))
            if len(toks) >= MIN_PARAGRAPH:
                out.append(Paragraph(rel, start, section, any(e in FLOATS for e in env_stack), toks))
            buf, start = [], 0

        for n, line in tex.iter_lines(path):
            if "\\begin{document}" in line:
                in_body = True
                continue
            if not in_body or stop:
                continue
            if "\\end{document}" in line:
                flush()
                stop = True
                continue
            if tex.BIBLIOGRAPHY_RE.search(line) or "\\begin{thebibliography}" in line:
                flush()
                after_bib = True
            if "\\appendix" in line:
                flush()
                after_bib = False
                continue
            if after_bib:
                continue
            for m in BEGIN_RE.finditer(line):
                if m.group(1) in SKIP_ENVS:
                    skip_depth += 1
                env_stack.append(m.group(1))
            for m in END_RE.finditer(line):
                if m.group(1) in SKIP_ENVS and skip_depth:
                    skip_depth -= 1
                if m.group(1) in env_stack:
                    env_stack.remove(m.group(1))
            if skip_depth:
                continue
            m = SECTION_RE.search(line)
            if m:
                flush()
                section = " ".join(_prose(m.group(2)).split()) or section
                continue
            if not line.strip():
                flush()
                continue
            if not buf:
                start = n
            buf.append(_prose(line))
        flush()
    return out


# --- alignment -----------------------------------------------------------------

def compare(old: list[str], paras: list[Paragraph]) -> tuple[list[Item], int]:
    """Classify every paragraph and every removed passage; return items and the unchanged count."""
    new: list[str] = []
    owner: list[int] = []
    for i, p in enumerate(paras):
        new += p.tokens
        owner += [i] * len(p.tokens)
    sm = SequenceMatcher(None, old, new, autojunk=False)
    matched_new = [False] * len(new)
    free_old = [True] * len(old)
    old_owner: dict[int, int] = {}                 # old index -> paragraph it aligned with
    diff_new: dict[int, list[str]] = {}
    diff_old: dict[int, list[str]] = {}
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal":
            for k in range(j2 - j1):
                matched_new[j1 + k] = True
                free_old[i1 + k] = False
                old_owner[i1 + k] = owner[j1 + k]
            continue
        for p in {owner[j] for j in range(j1, j2)}:
            span = [j for j in range(j1, j2) if owner[j] == p]
            diff_new.setdefault(p, []).extend(new[j] for j in span)
            diff_old.setdefault(p, []).extend(old[i1:i2])

    items: list[Item] = []
    unchanged = 0
    for idx, p in enumerate(paras):
        span = [j for j, o in enumerate(owner) if o == idx]
        kept = sum(matched_new[j] for j in span) / len(span)
        if kept >= UNCHANGED:
            unchanged += 1
            continue
        added, gone = diff_new.get(idx, []), diff_old.get(idx, [])
        numbers = any(t[0].isdigit() for t in set(added) ^ set(gone))
        if kept < NEW:
            status = "new"
        elif len(added) <= 3 and not numbers:
            status = "minor"
        else:
            status = "changed"
        items.append(Item(status, p.section, f"{p.file}:{p.line}", p.float, kept,
                          gone[:60] if status != "new" else [], added[:60], numbers))

    def free_runs() -> list[tuple[int, int]]:
        runs, i = [], 0
        while i < len(old):
            if free_old[i]:
                j = i
                while j < len(old) and free_old[j]:
                    j += 1
                runs.append((i, j))
                i = j
            else:
                i += 1
        return runs

    # A new paragraph whose text sits in a removed passage was moved, not written.
    for it in (i for i in items if i.status == "new"):
        para = next(p for p in paras if f"{p.file}:{p.line}" == it.where)
        for i1, i2 in free_runs():
            blocks = SequenceMatcher(None, old[i1:i2], para.tokens, autojunk=False).get_matching_blocks()
            if sum(b.size for b in blocks) / len(para.tokens) >= MOVED:
                for b in blocks:
                    for k in range(b.size):
                        free_old[i1 + b.a + k] = False
                it.status, it.new = "moved", []
                break

    for i1, i2 in free_runs():
        if i2 - i1 < MIN_CHUNK:
            continue
        before = next((old_owner[k] for k in range(i1 - 1, -1, -1) if k in old_owner), None)
        p = paras[before] if before is not None else None
        items.append(Item("removed", p.section if p else "Before the first matched paragraph",
                          f"after {p.file}:{p.line}" if p else "start", old=old[i1:i2][:60]))
    return items, unchanged


def render(items: list[Item], unchanged: int, main: str) -> str:
    counts = {s: sum(i.status == s for i in items)
              for s in ("changed", "minor", "new", "removed", "moved")}
    out = [f"# revision-diff: revision/previous.txt vs {main}",
           f"unchanged paragraphs: {unchanged} · " + " · ".join(f"{s}: {n}" for s, n in counts.items()),
           "Compared: prose, numbers, table and figure text (lowercase word and number tokens). "
           "Not compared: reference list, math, citations, figure images.", ""]
    order: list[str] = []
    for it in items:
        if it.section not in order:
            order.append(it.section)
    for sec in order:
        out.append(f"## {sec}")
        for it in (i for i in items if i.section == sec):
            flags = []
            if it.float:
                flags.append("table/figure: check the page")
            if it.numbers:
                flags.append("numbers differ")
            head = f"- [{it.status}] {it.where}"
            if it.kept is not None:
                head += f" ({round(it.kept * 100)}% of the tokens match)"
            if flags:
                head += " — " + "; ".join(flags)
            out.append(head)
            if it.old:
                out.append("    old: " + " ".join(it.old))
            if it.new:
                out.append("    new: " + " ".join(it.new))
        out.append("")
    return "\n".join(out)
