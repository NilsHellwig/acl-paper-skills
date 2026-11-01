"""Minimal lossless BibTeX handling.

Entries are kept as raw text so authoritative entries are never reformatted.
A file is parsed into a list of chunks: `Entry` objects and the plain text
between them (comments, @string, blank lines), which is written back verbatim.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_START = re.compile(r"@\s*([A-Za-z]+)\s*([{(])")
_PASSTHROUGH = {"comment", "string", "preamble"}


@dataclass
class Entry:
    type: str
    key: str
    raw: str

    def field(self, name: str) -> str | None:
        return field(self.raw, name)


class BibError(ValueError):
    pass


def _match_close(text: str, open_idx: int, opener: str) -> int:
    """Index of the delimiter closing the entry opened at `open_idx`."""
    if opener == "{":
        depth = 0
        for i in range(open_idx, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    return i
    else:
        braces = 0
        for i in range(open_idx + 1, len(text)):
            if text[i] == "{":
                braces += 1
            elif text[i] == "}":
                braces -= 1
            elif text[i] == ")" and braces == 0:
                return i
    raise BibError(f"Unbalanced braces in entry starting at offset {open_idx}.")


def parse(text: str) -> list:
    chunks: list = []
    pos = 0
    while True:
        m = _START.search(text, pos)
        if not m:
            break
        kind = m.group(1).lower()
        end = _match_close(text, m.end() - 1, m.group(2))
        if m.start() > pos:
            chunks.append(text[pos:m.start()])
        raw = text[m.start():end + 1]
        if kind in _PASSTHROUGH:
            chunks.append(raw)
        else:
            body = text[m.end():end]
            key = body.split(",", 1)[0].strip()
            if not key:
                raise BibError(f"Entry without key near: {raw[:60]!r}")
            chunks.append(Entry(kind, key, raw))
        pos = end + 1
    if pos < len(text):
        chunks.append(text[pos:])
    return chunks


def read(path: Path) -> list:
    if not path.exists():
        return []
    return parse(path.read_text(encoding="utf-8"))


def write(path: Path, chunks: list) -> None:
    out = "".join(c.raw if isinstance(c, Entry) else c for c in chunks)
    path.write_text(out, encoding="utf-8")


def entries(chunks: list) -> dict[str, Entry]:
    return {c.key: c for c in chunks if isinstance(c, Entry)}


def remove(chunks: list, key: str) -> Entry | None:
    """Remove the entry and the blank line that separated it from the previous one."""
    for i, c in enumerate(chunks):
        if isinstance(c, Entry) and c.key == key:
            del chunks[i]
            if i > 0 and isinstance(chunks[i - 1], str):
                chunks[i - 1] = chunks[i - 1].rstrip("\n") + "\n"
            return c
    return None


def append(chunks: list, entry: Entry) -> None:
    if chunks and isinstance(chunks[-1], str):
        chunks[-1] = chunks[-1].rstrip("\n") + "\n\n"
    elif chunks:
        chunks.append("\n\n")
    chunks.append(entry)
    chunks.append("\n")


def parse_single(text: str) -> Entry:
    found = [c for c in parse(text) if isinstance(c, Entry)]
    if len(found) != 1:
        raise BibError(f"Expected exactly one BibTeX entry, found {len(found)}.")
    entry = found[0]
    entry.raw = entry.raw.strip()
    return entry


def rekey(entry: Entry, new_key: str) -> Entry:
    m = _START.match(entry.raw)
    head, rest = entry.raw[:m.end()], entry.raw[m.end():]
    old_key_end = rest.index(entry.key) + len(entry.key)
    return Entry(entry.type, new_key, head + new_key + rest[old_key_end:])


def field(raw: str, name: str) -> str | None:
    m = re.search(rf"(?im)^\s*{re.escape(name)}\s*=\s*", raw)
    if not m:
        return None
    i = m.end()
    if i >= len(raw):
        return None
    opener = raw[i]
    if opener == "{":
        depth = 0
        for j in range(i, len(raw)):
            if raw[j] == "{":
                depth += 1
            elif raw[j] == "}":
                depth -= 1
                if depth == 0:
                    return _clean(raw[i + 1:j])
    elif opener == '"':
        depth = 0
        for j in range(i + 1, len(raw)):
            if raw[j] == "{":
                depth += 1
            elif raw[j] == "}":
                depth -= 1
            elif raw[j] == '"' and depth == 0:
                return _clean(raw[i + 1:j])
    else:
        m2 = re.match(r"[\w.-]+", raw[i:])
        return m2.group(0) if m2 else None
    return None


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("{", "").replace("}", "")).strip()


def normalize_title(title: str | None) -> str:
    return re.sub(r"[^a-z0-9]", "", (title or "").lower())
