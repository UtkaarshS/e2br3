"""Security and licensing guards: XXE-safe parsing, no bundled dictionaries."""
from __future__ import annotations

import re
from pathlib import Path

import pytest
from lxml import etree

import e2br3
from e2br3.parse import make_parser

PACKAGE = Path(e2br3.__file__).resolve().parent

MINIMAL = """<?xml version="1.0" encoding="UTF-8"?>
{doctype}
<MCCI_IN200100UV01 xmlns="urn:hl7-org:v3" ITSVersion="XML_1.0">
  <id extension="B1" root="2.16.840.1.113883.3.989.2.1.3.22"/>
  <PORR_IN049016UV>
    <id extension="M1" root="2.16.840.1.113883.3.989.2.1.3.1"/>
    <controlActProcess classCode="CACT" moodCode="EVN">
      <subject typeCode="SUBJ">
        <investigationEvent classCode="INVSTG" moodCode="EVN">
          <id extension="C1" root="2.16.840.1.113883.3.989.2.1.3.1"/>
          <text>{body}</text>
        </investigationEvent>
      </subject>
    </controlActProcess>
  </PORR_IN049016UV>
</MCCI_IN200100UV01>
"""

LOL = (
    '<!DOCTYPE MCCI_IN200100UV01 [<!ENTITY a "lol"><!ENTITY b "&a;&a;&a;&a;&a;&a;&a;&a;&a;&a;">'
    '<!ENTITY c "&b;&b;&b;&b;&b;&b;&b;&b;&b;&b;"><!ENTITY d "&c;&c;&c;&c;&c;&c;&c;&c;&c;&c;">]>'
)


def _doc(doctype: str, body: str) -> bytes:
    return MINIMAL.format(doctype=doctype, body=body).encode("utf-8")


@pytest.fixture
def xxe_doc(tmp_path: Path) -> bytes:
    secret = tmp_path / "secret.txt"
    secret.write_text("TOP-SECRET-CONTENT", encoding="utf-8")
    doctype = f'<!DOCTYPE MCCI_IN200100UV01 [<!ENTITY xxe SYSTEM "{secret.as_uri()}">]>'
    return _doc(doctype, "before &xxe; after")


def test_minimal_document_parses() -> None:
    icsr = e2br3.parse(_doc("", "plain narrative")).messages[0].icsr
    assert icsr.safety_report_id == "C1" and icsr.narrative == "plain narrative"


def test_external_entity_document_is_refused(xxe_doc: bytes) -> None:
    with pytest.raises(e2br3.E2BParseError, match="DTD") as exc:
        e2br3.parse(xxe_doc)
    assert "TOP-SECRET" not in str(exc.value)


def test_parser_itself_never_resolves_external_entities(xxe_doc: bytes) -> None:
    """Defence in depth: even before the DOCTYPE check, the entity is not loaded."""
    root = etree.fromstring(xxe_doc, make_parser())
    assert b"TOP-SECRET" not in etree.tostring(root)


def test_validate_refuses_dtd_without_resolving(xxe_doc: bytes) -> None:
    errors = e2br3.validate(xxe_doc)
    assert [e.kind for e in errors] == ["security"]
    assert all("TOP-SECRET" not in e.message for e in errors)


def test_internal_entity_bomb_is_refused() -> None:
    """A 'billion laughs' payload is refused instead of being expanded when read."""
    with pytest.raises(e2br3.E2BParseError, match="DTD"):
        e2br3.parse(_doc(LOL, "&d;"))


# --------------------------------------------------------------------------- licensing

DICTIONARY_NAMES = re.compile(
    r"(meddra|mdhier|llt|hlgt|edqm|whodrug|snomed|\.asc$|\.csv$|\.xlsx?$|\.zip$|\.db$|\.sqlite$)",
    re.IGNORECASE,
)


def test_no_dictionary_files_ship_in_the_package() -> None:
    """The MedDRA licence forbids redistribution; the package carries code only."""
    files = [p for p in PACKAGE.rglob("*") if p.is_file() and "__pycache__" not in p.parts]
    assert files, PACKAGE
    for p in files:
        rel = p.relative_to(PACKAGE).as_posix()
        assert p.suffix in {".py", ".typed"}, f"unexpected non-code file in package: {rel}"
        assert not DICTIONARY_NAMES.search(rel), rel
        assert p.stat().st_size < 100_000, f"suspiciously large file in package: {rel}"


def test_no_schemas_or_samples_in_the_package() -> None:
    assert not list(PACKAGE.rglob("*.xsd")) and not list(PACKAGE.rglob("*.xml"))
