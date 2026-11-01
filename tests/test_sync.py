from paperkit import bib, config, sync

ZHANG = """@inproceedings{zhang-etal-2021-aspect-sentiment,
    title = "Aspect Sentiment Quad Prediction as Paraphrase Generation",
    year = "2021",
}"""


def _keys(path):
    return set(bib.entries(bib.read(path)))


def test_uncited_moves_out_and_unknown_is_reported(project):
    root, cfg = project
    res = sync.run(root, cfg)
    assert res.moved_out == ["Aho:72"]
    assert set(res.unknown) == {"zhang-etal-2021-aspect-sentiment", "jones2021"}
    assert _keys(root / "custom.bib") == {"smith2020"}
    assert _keys(config.archive_bib(root, cfg)) == {"Aho:72"}


def test_archived_entry_moves_in_when_cited(project):
    root, cfg = project
    arch = config.archive_bib(root, cfg)
    arch.write_text(arch.read_text() + ZHANG + "\n")
    res = sync.run(root, cfg)
    assert "zhang-etal-2021-aspect-sentiment" in res.moved_in
    assert "zhang-etal-2021-aspect-sentiment" in _keys(root / "custom.bib")
    assert "zhang-etal-2021-aspect-sentiment" not in _keys(arch)


def test_roundtrip_out_and_back_in(project):
    root, cfg = project
    sync.run(root, cfg)
    main = root / "acl_latex.tex"
    main.write_text(main.read_text().replace(r"\section*{Limitations}", r"\citep{Aho:72}\section*{Limitations}"))
    res = sync.run(root, cfg)
    assert res.moved_in == ["Aho:72"]
    assert "Aho:72" in _keys(root / "custom.bib")


def test_second_run_is_a_no_op(project):
    root, cfg = project
    sync.run(root, cfg)
    before = (root / "custom.bib").read_text()
    res = sync.run(root, cfg)
    assert not res.changed
    assert (root / "custom.bib").read_text() == before


def test_nocite_star_keeps_everything(project):
    root, cfg = project
    main = root / "acl_latex.tex"
    main.write_text(main.read_text().replace(r"\bibliography", r"\nocite{*}\bibliography"))
    res = sync.run(root, cfg)
    assert res.moved_out == [] and res.nocite_all


def test_crossref_target_stays(project):
    root, cfg = project
    paper = root / "custom.bib"
    paper.write_text(paper.read_text().replace(
        "booktitle = {Proceedings of Something}", "crossref = {Aho:72}"))
    res = sync.run(root, cfg)
    assert "Aho:72" not in res.moved_out


def test_cited_but_unread_is_reported(project):
    root, cfg = project
    res = sync.run(root, cfg)
    assert "smith2020" in res.unread
    assert any("not read in full" in m for m in res.messages())
