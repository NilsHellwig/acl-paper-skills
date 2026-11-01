from paperkit import tex


def test_main_detection_and_mode(project):
    root, _ = project
    mains = tex.find_main_tex(root)
    assert [m.name for m in mains] == ["acl_latex.tex"]
    assert tex.acl_mode(mains[0]) == "review"
    assert tex.bib_names(mains[0]) == ["custom"]


def test_ordered_files_follow_input(project):
    root, cfg = project
    files = tex.ordered_files(root, root / cfg["main_tex"])
    assert [f.name for f in files] == ["acl_latex.tex", "method.tex"]


def test_citations_multiline_and_comments(project):
    root, cfg = project
    files = tex.ordered_files(root, root / cfg["main_tex"])
    cites, nocite_all = tex.citations(files)
    assert set(cites) == {"zhang-etal-2021-aspect-sentiment", "smith2020", "jones2021"}
    assert "commented-out" not in cites
    assert not nocite_all


def test_strip_comment_keeps_escaped_percent():
    assert tex.strip_comment(r"50\% of data % note") == r"50\% of data "
