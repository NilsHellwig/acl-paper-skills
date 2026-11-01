import pytest

from paperkit import bib

TEXT = """% header comment
@string{acl = "ACL"}

@inproceedings{a-key,
  title = {A {Nested} Title},
  author = "Doe, John and {\\"O}zt{\\"u}rk, Ay",
  year = 2021,
}

@misc(paren-key,
  title = {Paren (delimited) entry}
)
trailing text
"""


def test_roundtrip_is_lossless(tmp_path):
    p = tmp_path / "x.bib"
    p.write_text(TEXT)
    bib.write(p, bib.read(p))
    assert p.read_text() == TEXT


def test_entries_and_passthrough():
    chunks = bib.parse(TEXT)
    assert list(bib.entries(chunks)) == ["a-key", "paren-key"]
    assert any(isinstance(c, str) and c.startswith("@string") for c in chunks)


def test_field_handles_braces_quotes_and_bare_values():
    e = bib.entries(bib.parse(TEXT))["a-key"]
    assert e.field("title") == "A Nested Title"
    assert e.field("author").startswith("Doe, John and")
    assert e.field("year") == "2021"
    assert e.field("missing") is None


def test_rekey_changes_only_the_key():
    e = bib.parse_single("@article{old,\n  title = {old}\n}")
    new = bib.rekey(e, "new2024")
    assert new.key == "new2024"
    assert new.raw == "@article{new2024,\n  title = {old}\n}"


def test_parse_single_rejects_zero_or_many():
    with pytest.raises(bib.BibError):
        bib.parse_single("no entry here")
    with pytest.raises(bib.BibError):
        bib.parse_single("@a{x,}\n@b{y,}")


def test_unbalanced_entry_raises():
    with pytest.raises(bib.BibError):
        bib.parse("@article{x, title = {open")


def test_remove_and_append(tmp_path):
    chunks = bib.parse(TEXT)
    removed = bib.remove(chunks, "a-key")
    assert removed.key == "a-key"
    assert "a-key" not in bib.entries(chunks)
    bib.append(chunks, removed)
    assert list(bib.entries(chunks))[-1] == "a-key"


def test_normalize_title():
    assert bib.normalize_title("A {BERT}-based Model!") == "abertbasedmodel"
