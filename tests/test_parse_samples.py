"""FR-1: every public sample parses with 0 exceptions; batches with several messages work."""
from __future__ import annotations

import copy
import time
from pathlib import Path

import pytest
from lxml import etree

import e2br3
from e2br3.parse import make_parser
from conftest import (
    EMA,
    FDA,
    LIT_INITIAL,
    SCENARIO6,
    is_ack,
    params_or_skip,
    require,
    require_schemas,
    sample_xmls,
)

HL7 = "{urn:hl7-org:v3}"
ALL = sample_xmls()
ICSRS = [p for p in ALL if not is_ack(p)]
ACKS = [p for p in ALL if is_ack(p)]


@pytest.mark.parametrize("path", params_or_skip(ICSRS))
def test_sample_parses(path: Path) -> None:
    batch = e2br3.parse(path)
    assert isinstance(batch, e2br3.Batch)
    assert len(batch.messages) >= 1
    icsr = batch.messages[0].icsr
    assert icsr is not None
    assert icsr.safety_report_id  # C.1.1 is mandatory
    # The IG minimum case: at least one reaction and one drug (IG section 3.3.1).
    assert icsr.reactions and icsr.drugs
    # The model survives a JSON round trip unchanged.
    assert e2br3.Batch.model_validate_json(batch.model_dump_json()) == batch


@pytest.mark.parametrize("path", params_or_skip(ACKS))
def test_ack_is_rejected_cleanly(path: Path) -> None:
    """ACK messages are out of scope for v0.1: a clear E2BParseError, not a crash."""
    with pytest.raises(e2br3.E2BParseError, match="acknowledgement"):
        e2br3.parse(path)


def test_sample_counts() -> None:
    """The fetched set is the one the SRS was written against: 27 ICSR batches + 1 ACK."""
    if not ALL:
        pytest.skip("no sample fixtures")
    assert len(list(FDA.glob("*.xml"))) == 10
    assert len(list(EMA.glob("*.xml"))) == 11
    assert len(ICSRS) == 27
    assert len(ACKS) == 1


def test_parse_accepts_bytes() -> None:
    data = require(LIT_INITIAL).read_bytes()
    assert e2br3.parse(data) == e2br3.parse(LIT_INITIAL)


def test_not_well_formed_raises_parse_error() -> None:
    with pytest.raises(e2br3.E2BParseError, match="well-formed"):
        e2br3.parse(b"<MCCI_IN200100UV01 xmlns='urn:hl7-org:v3'>")


def test_wrong_root_raises_parse_error() -> None:
    with pytest.raises(e2br3.E2BParseError, match="expected"):
        e2br3.parse(b"<foo/>")


# --------------------------------------------------------------------------- synthetic batch


def build_multi_message_batch(first: Path, second: Path) -> bytes:
    """Batch wrapper of ``first`` holding the PORR_IN049016UV messages of both files.

    No public multi-message batch exists, so one is synthesised: the second
    file's message element(s) are appended after the first file's, before the
    batch receiver/sender elements (the order the XSD requires).
    """
    parser = make_parser()
    a = etree.parse(str(first), parser).getroot()
    b = etree.parse(str(second), parser).getroot()
    last = a.findall(f"{HL7}PORR_IN049016UV")[-1]
    for msg in reversed(b.findall(f"{HL7}PORR_IN049016UV")):
        last.addnext(copy.deepcopy(msg))
    return etree.tostring(a, xml_declaration=True, encoding="UTF-8")


@pytest.fixture
def multi_batch() -> bytes:
    return build_multi_message_batch(require(LIT_INITIAL), require(SCENARIO6))


def test_multi_message_batch(multi_batch: bytes) -> None:
    batch = e2br3.parse(multi_batch)
    assert len(batch.messages) == 2
    first, second = (m.icsr for m in batch.messages)
    assert first is not None and second is not None
    assert first.safety_report_id == "JP-DSJP-DSJ-2009-98765-1"
    assert second.safety_report_id == e2br3.parse(SCENARIO6).messages[0].icsr.safety_report_id
    # each message keeps its own header and its own cross-references
    assert batch.messages[0].message_id != batch.messages[1].message_id
    for icsr in (first, second):
        for drug in icsr.drugs:
            for dr in drug.relatedness:
                assert dr.reaction_index is not None
                assert icsr.reactions[dr.reaction_index].id == dr.reaction_id
    assert batch.icsrs == [first, second]


def test_multi_message_batch_is_schema_valid(multi_batch: bytes) -> None:
    require_schemas()
    assert e2br3.validate(multi_batch) == []


# --------------------------------------------------------------------------- cross-references


# KI-5 (docs/known-issues.md): this ICH example's reactions have ids "rid-N" but
# its G.k.9.i references say "r-idN", so they cannot resolve.
BROKEN_REFS = {"3_ExampleCase_Clinical_trial_v1_0.xml"}


def test_drug_reaction_matrix_resolves_reactions() -> None:
    """G.k.9.i refers to reactions by internal id; every reference resolves."""
    resolved = 0
    for path in ICSRS or [require(LIT_INITIAL)]:
        icsr = e2br3.parse(path).messages[0].icsr
        ids = [r.id for r in icsr.reactions]
        for drug in icsr.drugs:
            for dr in drug.relatedness:
                if path.name in BROKEN_REFS:
                    # kept raw, never guessed
                    assert dr.reaction_id not in ids and dr.reaction_index is None
                    continue
                assert dr.reaction_id in ids, (path.name, dr.reaction_id)
                assert icsr.reactions[dr.reaction_index].id == dr.reaction_id
                resolved += 1
    assert resolved > 0


def test_drug_role_resolved_for_every_drug() -> None:
    """G.k.1 sits outside the drug element and is joined back by id."""
    for path in ICSRS or [require(LIT_INITIAL)]:
        for drug in e2br3.parse(path).messages[0].icsr.drugs:
            assert drug.role is not None, (path.name, drug.id)


# --------------------------------------------------------------------------- performance


def test_scenario6_parse_time() -> None:
    """NFR: the ~2 MB FDA Scenario 6 'mega' file parses in under 0.5 s."""
    path = require(SCENARIO6)
    e2br3.parse(path)  # warm-up (imports, XPath compilation)
    best = min(_timed(path) for _ in range(3))
    print(f"\nFAERS2022Scenario6.xml ({path.stat().st_size / 1e6:.1f} MB) parse: {best * 1000:.1f} ms")
    assert best < 0.5


def _timed(path: Path) -> float:
    t0 = time.perf_counter()
    e2br3.parse(path)
    return time.perf_counter() - t0
