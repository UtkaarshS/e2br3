"""FR-3: every field is Value | NullFlavor | absent, never collapsed to None."""
from __future__ import annotations

from collections import Counter

import pytest
from lxml import etree

import e2br3
from e2br3 import Null, NullFlavor, Patient, Reaction, flavor_of, is_null
from conftest import EMA, FDA, ICH_EXAMPLES, LIT_INITIAL, require, sample_xmls

HL7 = "{urn:hl7-org:v3}"


# --------------------------------------------------------------------------- unit


def test_enum_is_exactly_the_ig_set() -> None:
    assert {f.value for f in NullFlavor} == {"NI", "MSK", "UNK", "NA", "ASKU", "NASK", "NINF", "PINF"}


def test_null_is_distinct_from_absent_and_from_text() -> None:
    p = Patient(name=Null(null_flavor=NullFlavor.NA))
    assert p.name is not None and is_null(p.name) and not p.name
    assert flavor_of(p.name) is NullFlavor.NA
    assert Patient().name is None  # absent
    # the string "NA" (say, initials) is a value, not a nullFlavor
    assert not is_null(Patient(name="NA").name)


def test_json_round_trip_keeps_the_three_states_apart() -> None:
    r = Reaction(results_in_death=Null(null_flavor=NullFlavor.NI), life_threatening=True, native_term="NA")
    back = Reaction.model_validate_json(r.model_dump_json())
    assert back == r
    assert is_null(back.results_in_death) and back.life_threatening is True
    assert back.native_term == "NA" and back.disabling is None


# --------------------------------------------------------------------------- samples

ALL_FLAVORS_IN_SAMPLES = {"NI", "MSK", "UNK", "NA", "ASKU", "NASK", "NINF", "PINF"}


def test_every_nullflavor_in_the_samples_is_an_ig_code() -> None:
    files = [p for p in sample_xmls() if "ACK" not in p.name]
    if not files:
        pytest.skip("no sample fixtures")
    seen: Counter[str] = Counter()
    for f in files:
        for el in etree.parse(str(f), etree.XMLParser(resolve_entities=False, no_network=True)).iter():
            if isinstance(el.tag, str) and el.get("nullFlavor"):
                seen[el.get("nullFlavor")] += 1
    assert set(seen) == ALL_FLAVORS_IN_SAMPLES
    for code in seen:
        NullFlavor(code)  # every one maps onto the enum


# Core-subset fields that carry a nullFlavor in the public samples.
CORE_CASES = [
    (ICH_EXAMPLES / "1-1_ExampleCase_literature_initial_v1_0.xml", lambda i: i.reactions[0].results_in_death, "NI"),
    (EMA / "10. ES-EMA-TESTCASE10.xml", lambda i: i.patient.name, "UNK"),
    (FDA / "FAERS2022Scenario6.xml", lambda i: i.reactions[1].start_date, "NASK"),
    (ICH_EXAMPLES / "2-1_ExampleCase_newNum_initial_v1_0.xml", lambda i: i.patient.name, "MSK"),
    (ICH_EXAMPLES / "2-1_ExampleCase_newNum_initial_v1_0.xml", lambda i: i.reactions[0].start_date, "ASKU"),
]


@pytest.mark.parametrize("path, get, flavor", CORE_CASES, ids=[c[2] for c in CORE_CASES])
def test_sample_core_field_flavor(path, get, flavor: str) -> None:
    value = get(e2br3.parse(require(path)).messages[0].icsr)
    assert isinstance(value, Null)
    assert value.null_flavor is NullFlavor(flavor)


# NA, NINF and PINF occur in the samples only outside the core subset (NINF/PINF
# are for F.r.3.2 ranges only), so each flavor is also injected into a core field.
@pytest.mark.parametrize("flavor", [f.value for f in NullFlavor])
def test_injected_flavor_on_core_field(flavor: str) -> None:
    tree = etree.parse(str(require(LIT_INITIAL)), etree.XMLParser(resolve_entities=False, no_network=True))
    name = tree.find(f".//{HL7}primaryRole/{HL7}player1/{HL7}name")  # D.1
    name.text = None
    name.set("nullFlavor", flavor)
    icsr = e2br3.parse(etree.tostring(tree)).messages[0].icsr
    assert icsr.patient.name == Null(null_flavor=NullFlavor(flavor))


def test_absent_element_is_none_not_null() -> None:
    icsr = e2br3.parse(require(LIT_INITIAL)).messages[0].icsr
    assert icsr.nullification_amendment is None  # C.1.11.1 not in an initial report
    assert icsr.drugs[0].dosages[0].text is None  # G.k.4.r.8 not sent


def test_unknown_nullflavor_is_a_clear_error() -> None:
    tree = etree.parse(str(require(LIT_INITIAL)), etree.XMLParser(resolve_entities=False, no_network=True))
    name = tree.find(f".//{HL7}primaryRole/{HL7}player1/{HL7}name")
    name.set("nullFlavor", "OTH")  # valid HL7, not allowed by the E2B(R3) IG
    with pytest.raises(e2br3.E2BParseError, match="OTH"):
        e2br3.parse(etree.tostring(tree))
