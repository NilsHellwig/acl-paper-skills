#!/usr/bin/env python3
"""paperkit: the command line every acl-paper skill calls.

Run it with any python3. Commands that need a source adapter (search, add,
anthology-update) re-run themselves under the interpreter set in
paper.config.json, where the adapter packages are installed.

    paperkit.py init --python PATH --main-tex FILE [--english us|uk]
    paperkit.py doctor
    paperkit.py search SOURCE QUERY [--limit N] [--year-from Y] [--year-to Y]
    paperkit.py add SOURCE ID [--key KEY]
    paperkit.py add-local PDF --key KEY
    paperkit.py bib-paste [--file F]                 (entry on stdin unless --file)
    paperkit.py mark-read KEY
    paperkit.py sync
    paperkit.py index
    paperkit.py check [FILE ...] [--json]
    paperkit.py guidelines NAME [NAME ...] [--out DIR]
    paperkit.py anthology-update
    paperkit.py test-source SOURCE QUERY ID          (adapter check, stores nothing)
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from paperkit import bib, checks, config, guidelines, literature, sources, sync, tex  # noqa: E402

TEMPLATES = HERE.parent / "templates"
ADAPTER_COMMANDS = {"search", "add", "anthology-update", "test-source"}


def die(msg: str, code: int = 1) -> None:
    print(msg, file=sys.stderr)
    sys.exit(code)


def ctx():
    try:
        root = config.require_root()
    except config.ConfigError as exc:
        die(f"⚠️ {exc}")
    return root, config.load(root)


def reexec_under_project_python(argv: list[str]) -> None:
    if os.environ.get("PAPERKIT_REEXEC") or not argv or argv[0] not in ADAPTER_COMMANDS:
        return
    root = config.find_root()
    if root is None:
        return
    py = config.load(root).get("python")
    if not py or Path(py).resolve() == Path(sys.executable).resolve():
        return
    if not Path(py).exists():
        die(f"⚠️ Configured python `{py}` does not exist. Re-run /acl-paper:init.")
    env = {**os.environ, "PAPERKIT_REEXEC": "1"}
    sys.exit(subprocess.call([py, __file__, *argv], env=env))


# --- commands ----------------------------------------------------------------

def cmd_init(a) -> None:
    root = Path.cwd().resolve()
    main = (root / a.main_tex).resolve()
    if not main.is_file():
        die(f"⚠️ {a.main_tex} does not exist.")
    names = tex.bib_names(main)
    if not names:
        die(f"⚠️ No \\bibliography{{...}} in {a.main_tex}. The ACL template has one.")
    bib_rel = os.path.relpath(main.parent / f"{names[-1]}.bib", root)
    cfg_path = root / config.CONFIG_NAME
    cfg = config.load(root) if cfg_path.exists() else dict(config.DEFAULTS)
    cfg.update(python=a.python, main_tex=os.path.relpath(main, root), bib=bib_rel,
               english=a.english)
    config.save(root, cfg)

    literature.ensure_layout(root, cfg)
    created = [config.CONFIG_NAME]
    archive = config.archive_bib(root, cfg)
    if not archive.exists():
        archive.write_text(sync.ARCHIVE_HEADER, encoding="utf-8")
        created.append(str(archive.relative_to(root)))
    report = root / cfg["report"]
    if not report.exists():
        shutil.copy(TEMPLATES / "report.md", report)
        created.append(cfg["report"])
    if not (root / bib_rel).exists():
        (root / bib_rel).write_text("", encoding="utf-8")
        created.append(bib_rel)
    literature.build_index(root, cfg, set())
    print(json.dumps({"root": str(root), "config": cfg, "written": created}, indent=2))


def cmd_doctor(a) -> None:
    root, cfg = ctx()
    ok = True

    def line(good: bool, msg: str) -> None:
        nonlocal ok
        ok &= good
        print(("✅ " if good else "⚠️ ") + msg)

    line(literature.pdftotext_available(),
         "pdftotext found" if literature.pdftotext_available() else
         "pdftotext missing (macOS: brew install poppler, Debian/Ubuntu: sudo apt install poppler-utils)")
    py = cfg.get("python")
    line(bool(py) and Path(py).exists(), f"python: {py}")
    line((root / cfg["main_tex"]).is_file(), f"main tex: {cfg['main_tex']}")
    line(config.paper_bib(root, cfg).exists(), f"paper bib: {cfg['bib']}")
    for name in cfg.get("sources", {}):
        try:
            path = sources.adapter_path(root, cfg, name)
        except sources.SourceError as exc:
            line(False, str(exc))
            continue
        if not path.is_file():
            line(False, f"source {name}: adapter {path} missing")
            continue
        missing = []
        for pkg in sources.requirements(path):
            mod = pkg.replace("-", "_")
            if py and Path(py).exists() and subprocess.call(
                [py, "-c", f"import {mod}"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            ):
                missing.append(pkg)
        line(not missing, f"source {name}" + (
            f": missing packages, install with `{py} -m pip install {' '.join(missing)}`"
            if missing else ""))
    if "acl-anthology" in cfg.get("sources", {}):
        data = Path(os.environ.get("ACL_PAPER_ANTHOLOGY_DIR",
                                   Path.home() / ".cache" / "acl-paper" / "anthology"))
        print(("✅ " if (data / "data").is_dir() else "ℹ️ ") + (
            f"Anthology data cached at {data}" if (data / "data").is_dir() else
            f"Anthology data not downloaded yet (~300 MB into {data} on first search)"))
    sys.exit(0 if ok else 1)


def _print_hits(name: str, hits: list[dict], known: dict) -> None:
    for i, h in enumerate(hits, 1):
        mark = ""
        if (name, h["id"]) in known:
            mark = f"  [already in library as `{known[(name, h['id'])]}`]"
        authors = ", ".join(h["authors"][:3]) + (" et al." if len(h["authors"]) > 3 else "")
        print(f"{i}. {h['title']} ({h['year']}){mark}\n   id: {h['id']}   venue: {h['venue']}\n"
              f"   authors: {authors}\n   {h['url']}")
        if h.get("abstract"):
            snippet = " ".join(h["abstract"].split())[:300]
            print(f"   abstract (triage only): {snippet}...")


def cmd_search(a) -> None:
    root, cfg = ctx()
    adapter = sources.load(root, cfg, a.source)
    hits = adapter.search(a.query, limit=a.limit, year_from=a.year_from, year_to=a.year_to)
    if not hits:
        print("No results.")
    _print_hits(a.source, hits, literature.known_ids(root, cfg))


def _store_entry(root, cfg, entry: bib.Entry) -> tuple[bib.Entry, str]:
    """Put `entry` into archive.bib unless an equal entry exists. Returns (entry, state)."""
    paper_p, arch_p = config.paper_bib(root, cfg), config.archive_bib(root, cfg)
    paper, arch = bib.read(paper_p), bib.read(arch_p) or [sync.ARCHIVE_HEADER]
    if entry.key in bib.entries(paper) or entry.key in bib.entries(arch):
        return entry, "exists"
    same_title = literature.titles(root, cfg).get(bib.normalize_title(entry.field("title")))
    if same_title:
        return entry, f"duplicate-title:{same_title}"
    bib.append(arch, entry)
    bib.write(arch_p, arch)
    return entry, "added"


def cmd_add(a) -> None:
    root, cfg = ctx()
    literature.ensure_layout(root, cfg)
    adapter = sources.load(root, cfg, a.source)
    known = literature.known_ids(root, cfg)
    if (a.source, a.id) in known:
        die(f"Already in library as `{known[(a.source, a.id)]}`.", 0)

    entry = bib.parse_single(adapter.bibtex(a.id))
    if a.key:
        entry = bib.rekey(entry, a.key)
    entry, state = _store_entry(root, cfg, entry)
    if state.startswith("duplicate-title"):
        die(f"⚠️ A bib entry with the same title exists as `{state.split(':', 1)[1]}`. "
            "Not added. Cite that key, or ask the user which version to keep.", 2)

    p = literature.paths(root, cfg, entry.key)
    if not p["pdf"].exists():
        with tempfile.TemporaryDirectory() as tmp:
            tmp_pdf = Path(tmp) / "paper.pdf"
            adapter.fetch_pdf(a.id, tmp_pdf)
            if not literature.is_pdf(tmp_pdf):
                die(f"⚠️ Download for {a.id} is not a PDF. BibTeX was stored, PDF was not.")
            shutil.move(str(tmp_pdf), p["pdf"])
    literature.convert(p["pdf"], p["md"])
    literature.create_notes(root, cfg, entry.key, entry.field("title") or "", a.source, a.id)
    sync.run(root, cfg)
    print(json.dumps({
        "key": entry.key, "bib": "already present" if state == "exists" else "added to archive.bib",
        "pdf": str(p["pdf"].relative_to(root)), "md": str(p["md"].relative_to(root)),
        "notes": str(p["notes"].relative_to(root)), "status": literature.status(root, cfg, entry.key),
    }, indent=2))


def cmd_add_local(a) -> None:
    root, cfg = ctx()
    literature.ensure_layout(root, cfg)
    pdf = Path(a.pdf).resolve()
    if not pdf.is_file() or not literature.is_pdf(pdf):
        die(f"⚠️ {a.pdf} is not a PDF file.")
    all_entries = {**bib.entries(bib.read(config.archive_bib(root, cfg))),
                   **bib.entries(bib.read(config.paper_bib(root, cfg)))}
    if a.key not in all_entries:
        die(f"⚠️ No BibTeX entry `{a.key}` yet. Ask the user for the authoritative entry and "
            "add it with `bib-paste` first.", 2)
    p = literature.paths(root, cfg, a.key)
    shutil.move(str(pdf), p["pdf"])
    literature.convert(p["pdf"], p["md"])
    literature.create_notes(root, cfg, a.key, all_entries[a.key].field("title") or "",
                            "local", a.key)
    sync.run(root, cfg)
    print(json.dumps({k: str(v.relative_to(root)) for k, v in p.items()}, indent=2))


def cmd_bib_paste(a) -> None:
    root, cfg = ctx()
    text = Path(a.file).read_text(encoding="utf-8") if a.file else sys.stdin.read()
    entry, state = _store_entry(root, cfg, bib.parse_single(text))
    if state.startswith("duplicate-title"):
        die(f"⚠️ Same title already stored as `{state.split(':', 1)[1]}`. Not added.", 2)
    print(f"`{entry.key}`: {'already present' if state == 'exists' else 'added to archive.bib'}")
    sync.run(root, cfg)


def cmd_mark_read(a) -> None:
    root, cfg = ctx()
    problems = literature.mark_read(root, cfg, a.key)
    if problems:
        die("⚠️ Not marked read-full:\n- " + "\n- ".join(problems), 2)
    sync.run(root, cfg)
    print(f"`{a.key}` is read-full.")


def cmd_sync(a) -> None:
    root, cfg = ctx()
    res = sync.run(root, cfg)
    print("\n".join(res.messages()) or "Bib in sync. All cited papers read in full.")


def cmd_index(a) -> None:
    root, cfg = ctx()
    files = tex.all_tex_files(root, root / cfg["main_tex"], config.lit_dir(root, cfg))
    print(literature.build_index(root, cfg, set(tex.citations(files)[0])))


def cmd_check(a) -> None:
    root, cfg = ctx()
    found = checks.run(root, cfg, [Path(f) for f in a.files] or None)
    if a.json:
        print(json.dumps([f.__dict__ for f in found], indent=2, ensure_ascii=False))
        return
    order = {"high": 0, "medium": 1, "low": 2}
    for f in sorted(found, key=lambda f: (order[f.severity], f.file, f.line)):
        print(f"[{f.severity}] {f.category} {f.check} {f.file}:{f.line} `{f.text}` {f.hint}")
    print(f"{len(found)} candidate findings.")


def cmd_guidelines(a) -> None:
    fetched, failed = guidelines.fetch(a.names, Path(a.out) if a.out else None)
    for name, path in fetched.items():
        print(f"✅ {name}: {path}")
    for name, why in failed.items():
        print(f"⚠️ {name}: {why}")
    if failed:
        print("⚠️ Some upstream documents could not be fetched. Do not fall back to "
              "remembered guidelines: tell the user which ones are missing.")
        sys.exit(1)


def cmd_test_source(a) -> None:
    """Exercise an adapter end to end without touching the library."""
    root, cfg = ctx()
    adapter = sources.load(root, cfg, a.source)
    hits = adapter.search(a.query, limit=2)
    print(f"✅ search: {len(hits)} hits")
    for h in hits:
        missing = {"id", "title", "authors", "year", "venue", "url"} - set(h)
        if missing:
            die(f"⚠️ hit lacks fields: {', '.join(sorted(missing))}")
    entry = bib.parse_single(adapter.bibtex(a.id))
    print(f"✅ bibtex: @{entry.type}{{{entry.key}, ...}} title: {entry.field('title')}")
    with tempfile.TemporaryDirectory() as tmp:
        pdf = Path(tmp) / "t.pdf"
        adapter.fetch_pdf(a.id, pdf)
        if not literature.is_pdf(pdf):
            die("⚠️ fetch_pdf wrote something that is not a PDF.")
        print(f"✅ fetch_pdf: {pdf.stat().st_size // 1024} KB PDF")


def cmd_anthology_update(a) -> None:
    root, cfg = ctx()
    adapter = sources.load(root, cfg, "acl-anthology")
    adapter.update_data()
    print(f"Anthology data updated in {adapter.DATA_DIR}")


def main(argv: list[str]) -> None:
    reexec_under_project_python(argv)
    ap = argparse.ArgumentParser(prog="paperkit.py", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("init")
    s.add_argument("--python", required=True)
    s.add_argument("--main-tex", required=True)
    s.add_argument("--english", choices=["us", "uk"], default="us")
    sub.add_parser("doctor")
    s = sub.add_parser("search")
    s.add_argument("source")
    s.add_argument("query")
    s.add_argument("--limit", type=int, default=10)
    s.add_argument("--year-from", type=int)
    s.add_argument("--year-to", type=int)
    s = sub.add_parser("add")
    s.add_argument("source")
    s.add_argument("id")
    s.add_argument("--key")
    s = sub.add_parser("add-local")
    s.add_argument("pdf")
    s.add_argument("--key", required=True)
    s = sub.add_parser("bib-paste")
    s.add_argument("--file")
    s = sub.add_parser("mark-read")
    s.add_argument("key")
    sub.add_parser("sync")
    sub.add_parser("index")
    s = sub.add_parser("check")
    s.add_argument("files", nargs="*")
    s.add_argument("--json", action="store_true")
    s = sub.add_parser("guidelines")
    s.add_argument("names", nargs="+")
    s.add_argument("--out")
    sub.add_parser("anthology-update")
    s = sub.add_parser("test-source")
    s.add_argument("source")
    s.add_argument("query")
    s.add_argument("id")

    a = ap.parse_args(argv)
    handler = globals()["cmd_" + a.cmd.replace("-", "_")]
    try:
        handler(a)
    except (bib.BibError, sources.SourceError, LookupError, config.ConfigError) as exc:
        die(f"⚠️ {exc}")


if __name__ == "__main__":
    main(sys.argv[1:])
