from paperkit import checks


def _found(project, **kw):
    root, cfg = project
    return {(f.check, f.text) for f in checks.run(root, {**cfg, **kw})}


def test_planted_errors_are_found(project):
    found = _found(project)
    expected = {
        ("leftover-marker", "TODO"),
        ("duplicate-word", "the the"),
        ("plain-text-citation", "Smith et al. (2020)"),
        ("em-dash", "---"),
        ("ai-vocabulary", "delve"),
        ("spelling-variant", "analyse"),
        ("abbreviation", "BERT"),
        ("cited-unread", "smith2020"),
    }
    assert expected <= found


def test_introduced_abbreviations_are_not_flagged(project):
    found = _found(project)
    assert ("abbreviation", "LLM") not in found
    assert ("abbreviation", "ASQP") not in found


def test_preamble_is_skipped(project):
    assert not any(t in ("AND", "ZZTOP") for _, t in _found(project))


def test_uk_flags_us_spelling(project):
    root, cfg = project
    (root / "sections" / "method.tex").write_text("We analyze it.\n")
    found = _found(project, english="uk")
    assert ("spelling-variant", "analyze") in found


def test_missing_limitations(project):
    root, _ = project
    main = root / "acl_latex.tex"
    main.write_text(main.read_text().replace(r"\section*{Limitations}", ""))
    assert any(c == "missing-limitations" for c, _ in _found(project))


def test_scope_limits_findings(project):
    root, cfg = project
    only = [root / "sections" / "method.tex"]
    assert all(f.file == "sections/method.tex" for f in checks.run(root, cfg, only)
               if f.check != "missing-limitations")


def test_english_detection_recommends_majority(project):
    root, cfg = project
    (root / "sections" / "method.tex").write_text(
        "We analyse the modelling, the behaviour and the colour of tokenisation. We analyze it.\n")
    usage = checks.english_usage(root, root / cfg["main_tex"])
    assert usage["recommendation"] == "uk"
    assert (usage["us_count"], usage["uk_count"]) == (1, 5)
    assert "83%" in usage["reason"]


def test_english_detection_defaults_to_us_without_evidence(project):
    root, cfg = project
    (root / "sections" / "method.tex").write_text("Plain text.\n")
    usage = checks.english_usage(root, root / cfg["main_tex"])
    assert usage["recommendation"] == "us" and usage["us_count"] == usage["uk_count"] == 0
