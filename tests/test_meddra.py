"""FR-4: coded values are code + OID + version + displayName; MedDRA LLT codes round-trip unchanged."""
from __future__ import annotations

from pathlib import Path

import pytest
from lxml import etree

import e2br3
from e2br3 import Coded
from e2br3.mapping import OID_MEDDRA, OID_OBS
from conftest import LIT_INITIAL, is_ack, params_or_skip, require, sample_xmls

NS = {"h": "urn:hl7-org:v3"}
REACTION_VALUES = etree.XPath(
    f"//h:primaryRole/h:subjectOf2/h:observation[h:code[@code='29'][@codeSystem='{OID_OBS}']]/h:value",
    namespaces=NS,
)
ICSRS = [p for p in sample_xmls() if not is_ack(p)]


@pytest.mark.parametrize("path", params_or_skip(ICSRS))
def test_reaction_meddra_codes_round_trip(path: Path) -> None:
    raw = [
        (v.get("code"), v.get("codeSystem"), v.get("codeSystemVersion"), v.get("displayName"))
        for v in REACTION_VALUES(etree.parse(str(path), etree.XMLParser(resolve_entities=False, no_network=True)))
    ]
    batch = e2br3.parse(path)
    parsed = [
        (c.code, c.code_system, c.code_system_version, c.display_name) if isinstance(c, Coded) else c
        for c in (r.meddra for r in batch.messages[0].icsr.reactions)
    ]
    assert parsed == raw
    # and unchanged through JSON
    again = e2br3.Batch.model_validate_json(batch.model_dump_json())
    assert [r.meddra for r in again.messages[0].icsr.reactions] == [r.meddra for r in batch.messages[0].icsr.reactions]


def test_meddra_code_is_opaque_text() -> None:
    rx = e2br3.parse(require(LIT_INITIAL)).messages[0].icsr.reactions[0]
    assert rx.meddra == Coded(
        code="10022617",
        code_system=OID_MEDDRA,
        code_system_version="15",
        display_name=None,  # not in the XML, so not invented: no dictionary lookup
        original_text="間質性肺炎",
    )
    assert rx.meddra_code == "10022617" and isinstance(rx.meddra_code, str)
    assert rx.meddra_version == "15"


def test_codes_keep_leading_zeros() -> None:
    """Coded values are strings: the ICH route code '048' must not become 48."""
    drug = e2br3.parse(require(LIT_INITIAL)).messages[0].icsr.drugs[0]
    assert drug.dosages[0].route.code == "048"
