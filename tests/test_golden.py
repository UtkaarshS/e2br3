"""FR-2: core fields match the ICH Example Instances v2.0 golden spreadsheets.

The spreadsheets are not readable without openpyxl/xlrd (not dependencies), so
their core-subset cells were transcribed once into ``tests/golden/ich_examples.json``
with the spreadsheet row and column of every value. Entries marked
``known_issue`` are spreadsheet errors or IG ambiguities described in
``docs/known-issues.md``; they are asserted to still differ, so a fix on either
side is noticed.
"""
from __future__ import annotations

import json
import re
from decimal import Decimal
from typing import Any, Optional

import pytest

import e2br3
from e2br3 import Batch, Coded, Null, TS
from conftest import GOLDEN, ICH_EXAMPLES, require

GOLDEN_FILE = GOLDEN / "ich_examples.json"
DATA = json.loads(GOLDEN_FILE.read_text(encoding="utf-8"))
_CACHE: dict[str, Batch] = {}


def _batch(xml_name: str) -> Batch:
    if xml_name not in _CACHE:
        _CACHE[xml_name] = e2br3.parse(require(ICH_EXAMPLES / xml_name))
    return _CACHE[xml_name]


def render(v: Any) -> Optional[str]:
    """Reduce a parsed value to the string a spreadsheet cell shows."""
    if v is None:
        return None
    if isinstance(v, Null):
        return v.null_flavor.value
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, TS):
        return v.raw
    if isinstance(v, Coded):
        return v.code if v.code is not None else v.original_text
    if isinstance(v, Decimal):
        return format(v, "f")
    return str(v)


def _attr(obj: Any, name: str) -> Any:
    """Attribute of a value that may be Null/None (propagates the Null/None)."""
    if obj is None or isinstance(obj, Null):
        return obj
    return getattr(obj, name)


def _nth(items: list, n: int) -> Any:
    return items[n - 1] if len(items) >= n else None


def actual(batch: Batch, eid: str, n: int) -> Any:
    """The parsed value for golden element ``eid``, iteration ``n``."""
    msg = batch.messages[0]
    icsr = msg.icsr
    assert icsr is not None
    rx = _nth(icsr.reactions, n)
    drug = _nth(icsr.drugs, n)
    dosage = _nth(drug.dosages, 1) if drug else None
    matrix = [(d, dr, a) for d in icsr.drugs for dr in d.relatedness for a in dr.assessments]
    cell = _nth(matrix, n)
    src = _nth(icsr.primary_sources, n)
    lit = _nth(icsr.literature, n)
    table = {
        "N.1.1": lambda: batch.batch_type,
        "N.1.2": lambda: batch.batch_number,
        "N.1.3": lambda: batch.sender,
        "N.1.4": lambda: batch.receiver,
        "N.1.5": lambda: batch.transmission_date,
        "N.2.r.1": lambda: msg.message_id,
        "N.2.r.2": lambda: msg.sender,
        "N.2.r.3": lambda: msg.receiver,
        "N.2.r.4": lambda: msg.creation_date,
        "C.1.1": lambda: icsr.safety_report_id,
        "C.1.2": lambda: icsr.creation_date,
        "C.1.3": lambda: icsr.report_type,
        "C.1.4": lambda: icsr.first_received_date,
        "C.1.5": lambda: icsr.most_recent_date,
        "C.1.8.1": lambda: icsr.worldwide_case_id,
        "C.1.11.1": lambda: icsr.nullification_amendment,
        "C.1.11.2": lambda: icsr.nullification_reason,
        "C.2.r.3": lambda: src.country,
        "C.2.r.4": lambda: src.qualification,
        "C.4.r.1": lambda: lit.reference,
        "C.4.r.2": lambda: _attr(lit.document, "data"),
        "D.1": lambda: icsr.patient.name,
        "D.2.2a": lambda: _attr(icsr.patient.age, "value"),
        "D.2.2b": lambda: _attr(icsr.patient.age, "unit"),
        "D.5": lambda: icsr.patient.sex,
        "E.i.1.1a": lambda: rx.native_term,
        "E.i.1.1b": lambda: rx.native_language,
        "E.i.1.2": lambda: rx.translated_term,
        "E.i.2.1a": lambda: _attr(rx.meddra, "code_system_version"),
        "E.i.2.1b": lambda: _attr(rx.meddra, "code"),
        "E.i.3.2a": lambda: rx.results_in_death,
        "E.i.3.2b": lambda: rx.life_threatening,
        "E.i.3.2c": lambda: rx.hospitalisation,
        "E.i.3.2d": lambda: rx.disabling,
        "E.i.3.2e": lambda: rx.congenital_anomaly,
        "E.i.3.2f": lambda: rx.other_medically_important,
        "E.i.4": lambda: rx.start_date,
        "E.i.5": lambda: rx.end_date,
        "E.i.7": lambda: rx.outcome,
        "G.k.1": lambda: drug.role,
        "G.k.2.2": lambda: drug.product_name,
        "G.k.2.3.r.1": lambda: _nth(drug.substances, 1),
        "G.k.4.r.8": lambda: dosage.text,
        "G.k.4.r.10.1": lambda: dosage.route_text,
        "G.k.4.r.10.2a": lambda: _attr(dosage.route, "code_system_version"),
        "G.k.4.r.10.2b": lambda: _attr(dosage.route, "code"),
        "G.k.8": lambda: drug.action_taken,
        "G.k.9.i.1": lambda: _reaction_term(icsr, cell[1]),
        "G.k.9.i.2.r.1": lambda: cell[2].source,
        "G.k.9.i.2.r.2": lambda: cell[2].method,
        "G.k.9.i.2.r.3": lambda: cell[2].result,
        "H.1": lambda: icsr.narrative,
    }
    try:
        return table[eid]()
    except (AttributeError, TypeError):  # the group/iteration itself is missing
        return None


def _reaction_term(icsr: Any, dr: Any) -> Any:
    if dr.reaction_index is None:
        return None
    rx = icsr.reactions[dr.reaction_index]
    return rx.native_term if rx.native_term is not None else rx.translated_term


def norm(s: Optional[str]) -> Optional[str]:
    return None if s is None else re.sub(r"\s+", " ", s).strip()


CASES = [
    pytest.param(xml, entry, id=f"{xml[:3].rstrip('_')}:{entry['id']}#{entry['n']}@{entry['col']}{entry['row']}")
    for xml, spec in DATA["files"].items()
    for entry in spec["values"]
]


@pytest.mark.parametrize("xml_name, entry", CASES)
def test_golden_value(xml_name: str, entry: dict) -> None:
    got = norm(render(actual(_batch(xml_name), entry["id"], entry["n"])))
    want = norm(entry["value"])
    if entry.get("known_issue"):
        assert got != want, f"{entry['known_issue']} no longer reproduces; update docs/known-issues.md"
    else:
        assert got == want


def test_golden_match_rate(capsys: pytest.CaptureFixture[str]) -> None:
    """Report the match rate across all transcribed cells (known issues count as misses)."""
    total = matched = 0
    for xml, spec in DATA["files"].items():
        batch = _batch(xml)
        for entry in spec["values"]:
            total += 1
            matched += norm(render(actual(batch, entry["id"], entry["n"]))) == norm(entry["value"])
    known = sum(bool(e.get("known_issue")) for s in DATA["files"].values() for e in s["values"])
    with capsys.disabled():
        print(f"\ngolden match: {matched}/{total} = {matched / total:.1%} ({known} known issues)")
    assert matched == total - known
