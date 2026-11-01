from paperkit import literature


def _notes(root, cfg, key="smith2020"):
    p = literature.create_notes(root, cfg, key, "A Title", "local", key)
    literature.paths(root, cfg, key)["md"].write_text("full text")
    return p


def test_safe_name():
    assert literature.safe_name("10.1561/150:0011") == "10.1561_150_0011"


def test_mark_read_refuses_empty_notes(project):
    root, cfg = project
    _notes(root, cfg)
    problems = literature.mark_read(root, cfg, "smith2020")
    assert len(problems) == 2
    assert literature.status(root, cfg, "smith2020") == literature.STATUS_FETCHED


def test_mark_read_refuses_without_text(project):
    root, cfg = project
    p = _notes(root, cfg)
    literature.paths(root, cfg, "smith2020")["md"].unlink()
    p.write_text(p.read_text().replace("## Read\n", "## Read\n\nFull.\n").replace(
        "## Claims this paper supports\n", "## Claims this paper supports\n\n- X (Sec. 2): \"x\"\n"))
    assert any("missing" in m for m in literature.mark_read(root, cfg, "smith2020"))


def test_mark_read_accepts_filled_notes(project):
    root, cfg = project
    p = _notes(root, cfg)
    p.write_text(p.read_text().replace("## Read\n", "## Read\n\nFull paper.\n").replace(
        "## Claims this paper supports\n",
        "## Claims this paper supports\n\n- Introduces X (Sec. 3, p. 4): \"we introduce\"\n"))
    assert literature.mark_read(root, cfg, "smith2020") == []
    assert literature.status(root, cfg, "smith2020") == literature.STATUS_READ


def test_index_lists_notes(project):
    root, cfg = project
    _notes(root, cfg)
    index = literature.build_index(root, cfg, {"smith2020"})
    text = index.read_text()
    assert "`smith2020`" in text and "| yes |" in text and "⚠️ missing" in text


def test_known_ids(project):
    root, cfg = project
    literature.create_notes(root, cfg, "k1", "T", "arxiv", "1706.03762")
    assert literature.known_ids(root, cfg) == {("arxiv", "1706.03762"): "k1"}
