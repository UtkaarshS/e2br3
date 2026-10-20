"""FR-5: validate() against the local ICH XSD v2.5, with line numbers."""
from __future__ import annotations

from pathlib import Path

import pytest

import e2br3
from e2br3.validate import load_schema
from conftest import EMA, LIT_INITIAL, params_or_skip, require, require_schemas, sample_xmls


@pytest.fixture(autouse=True)
def _schemas() -> None:
    require_schemas()


@pytest.mark.parametrize("path", params_or_skip(sample_xmls()))
def test_samples_are_valid(path: Path) -> None:
    """All public samples (27 ICSR batches and the ACK, each against its own root XSD) pass."""
    assert e2br3.validate(path) == []


def _mutate(old: str, new: str) -> bytes:
    text = require(LIT_INITIAL).read_text(encoding="utf-8")
    assert text.count(old) == 1, old
    return text.replace(old, new).encode("utf-8")


def _line_of(data: bytes, needle: str) -> int:
    return next(i for i, line in enumerate(data.decode("utf-8").splitlines(), 1) if needle in line)


def test_bad_timestamp_is_reported_on_its_line() -> None:
    data = _mutate('<creationTime value="20120720100000"/>', '<creationTime value="2012-07-20"/>')
    errors = e2br3.validate(data)
    assert errors, "a TS with dashes must fail the XSD pattern"
    assert errors[0].line == _line_of(data, 'value="2012-07-20"')
    assert errors[0].kind == "schema"
    assert "2012-07-20" in errors[0].message


def test_unexpected_element_is_reported_on_its_line() -> None:
    data = _mutate('<responseModeCode code="D"/>', '<responseModeCode code="D"/><bogusElement/>')
    errors = e2br3.validate(data)
    assert len(errors) >= 1
    assert errors[0].line == _line_of(data, "<bogusElement/>")
    assert "bogusElement" in errors[0].message


def test_missing_mandatory_element_fails() -> None:
    data = _mutate('<interactionId extension="MCCI_IN200100UV01" root="2.16.840.1.113883.1.6"/>', "")
    errors = e2br3.validate(data)
    assert errors and all(isinstance(e.line, int) for e in errors)


def test_bad_attribute_value_fails() -> None:
    data = _mutate('<administrativeGenderCode code="2" codeSystem="1.0.5218"/>',
                   '<administrativeGenderCode code="2" codeSystem="not an oid"/>')
    errors = e2br3.validate(data)
    assert errors and errors[0].line == _line_of(data, 'codeSystem="not an oid"')


def test_not_well_formed_is_a_syntax_error_not_an_exception() -> None:
    errors = e2br3.validate(b"<MCCI_IN200100UV01 xmlns='urn:hl7-org:v3'>\n<id>\n")
    assert len(errors) == 1 and errors[0].kind == "syntax" and errors[0].line is not None


def test_remote_schema_location_is_ignored() -> None:
    """EMA samples point at a remote XSD URL; validation must not need the network."""
    path = require(EMA / "01A. SE-EMA-TESTCASE01A.xml")
    assert "https://" in path.read_text(encoding="utf-8")[:2000]
    assert e2br3.validate(path) == []


def test_schema_is_cached() -> None:
    e2br3.validate(require(LIT_INITIAL))
    before = load_schema.cache_info().hits
    e2br3.validate(require(LIT_INITIAL))
    assert load_schema.cache_info().hits == before + 1


def test_explicit_missing_schema_dir_raises(tmp_path: Path) -> None:
    with pytest.raises(e2br3.SchemaNotFoundError):
        e2br3.validate(require(LIT_INITIAL), schema_dir=tmp_path)
