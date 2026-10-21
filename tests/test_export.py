"""FR-6: to_dict / to_json / to_rows / to_frames.

Row counts are checked against the source XML with XPath written here,
independently of the mapping table in ``e2br3.mapping``.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest
from lxml import etree

import e2br3
from e2br3 import Null, NullFlavor
from e2br3.export import COLUMNS, TABLES
from conftest import EMA, FDA, LIT_INITIAL, is_ack, params_or_skip, require, sample_xmls

ICSRS = [p for p in sample_xmls() if not is_ack(p)]
NS = {"h": "urn:hl7-org:v3"}
OBS = "2.16.840.1.113883.3.989.2.1.1.19"  # ICH code list 19 (observation codes)
ORG = "2.16.840.1.113883.3.989.2.1.1.20"  # ICH code list 20 (organizer codes)

COUNT_CASES = etree.XPath("count(//h:controlActProcess/h:subject/h:investigationEvent)", namespaces=NS)
COUNT_REACTIONS = etree.XPath(  # E.i: observation code 29 under the patient role
    f"count(//h:primaryRole/h:subjectOf2/h:observation[h:code[@code='29' and @codeSystem='{OBS}']])",
    namespaces=NS,
)
COUNT_DRUGS = etree.XPath(  # G.k: substanceAdministration in the drug organizer (code 4)
    f"count(//h:primaryRole/h:subjectOf2/h:organizer[h:code[@code='4' and @codeSystem='{ORG}']]"
    "/h:component/h:substanceAdministration)",
    namespaces=NS,
)
COUNT_ASSESSMENTS = etree.XPath(  # G.k.9.i.2: causalityAssessment code 39
    f"count(//h:adverseEventAssessment/h:component/h:causalityAssessment[h:code[@code='39' and @codeSystem='{OBS}']])",
    namespaces=NS,
)

HAS_PANDAS = importlib.util.find_spec("pandas") is not None
needs_pandas = pytest.mark.skipif(
    not HAS_PANDAS, reason="pandas not installed (optional extra: pip install 'e2br3[pandas]'); to_rows() is tested instead"
)


def _tree(path: Path) -> etree._ElementTree:
    return etree.parse(str(path), etree.XMLParser(resolve_entities=False, no_network=True))


@pytest.mark.parametrize("path", params_or_skip(ICSRS))
def test_row_counts_match_source_xml(path: Path) -> None:
    tree = _tree(path)
    rows = e2br3.parse(path).to_rows(path.name)
    assert len(rows["cases"]) == int(COUNT_CASES(tree))
    assert len(rows["reactions"]) == int(COUNT_REACTIONS(tree))
    assert len(rows["drugs"]) == int(COUNT_DRUGS(tree))
    assert len(rows["drug_reaction"]) == int(COUNT_ASSESSMENTS(tree))
    for table in TABLES:
        for row in rows[table]:
            assert tuple(row) == COLUMNS[table]
            assert row["case_key"] == f"{path.name}#{rows['cases'][0]['safety_report_id']}"


@pytest.mark.parametrize("path", params_or_skip(ICSRS))
def test_json_round_trip(path: Path) -> None:
    batch = e2br3.parse(path)
    text = batch.to_json()
    assert e2br3.Batch.model_validate_json(text) == batch
    assert json.loads(text) == batch.to_dict() == e2br3.to_dict(batch)
    json.dumps(batch.to_dict())  # JSON-safe: plain dict/list/str/number/bool/None only


@pytest.mark.parametrize("path", params_or_skip(ICSRS))
@needs_pandas
def test_frames_match_rows(path: Path) -> None:
    batch = e2br3.parse(path)
    frames = batch.to_frames(path.name)
    rows = batch.to_rows(path.name)
    assert set(frames) == set(TABLES)
    for table in TABLES:
        assert len(frames[table]) == len(rows[table])
        assert tuple(frames[table].columns) == COLUMNS[table]


def test_nullflavor_survives_export() -> None:
    path = require(EMA / "10. ES-EMA-TESTCASE10.xml")  # D.1 patient name is nullFlavor=UNK
    batch = e2br3.parse(path)
    d = batch.to_dict()
    patient = d["messages"][0]["icsr"]["patient"]
    assert patient["name"] == {"nullFlavor": "UNK"}
    back = e2br3.Batch.model_validate_json(batch.to_json())
    assert back.messages[0].icsr.patient.name == Null(null_flavor=NullFlavor.UNK)
    assert batch.to_rows()["cases"][0]["patient_name"] == "nullFlavor=UNK"


def test_null_absent_and_text_stay_distinct_in_json() -> None:
    p = e2br3.Patient(name="NA", sex=Null(null_flavor=NullFlavor.NA))
    d = p.to_dict()
    assert d["name"] == "NA"
    assert d["sex"] == {"nullFlavor": "NA"}
    assert d["age"] is None  # absent
    assert e2br3.Patient.model_validate_json(p.to_json()) == p


def test_reaction_nullflavor_in_rows() -> None:
    rows = e2br3.parse(require(LIT_INITIAL)).to_rows("lit.xml")
    assert rows["reactions"][0]["results_in_death"] == "nullFlavor=NI"
    assert rows["reactions"][0]["meddra_code"] == "10022617"
    assert rows["drugs"][0]["route"] == "048"  # leading zero kept


def test_case_key_defaults_to_batch_number() -> None:
    batch = e2br3.parse(require(LIT_INITIAL))
    key = batch.to_rows()["cases"][0]["case_key"]
    assert key == f"{batch.batch_number}#JP-DSJP-DSJ-2009-98765-1"


def test_repeated_case_id_in_one_batch_gets_suffix() -> None:
    batch = e2br3.parse(require(LIT_INITIAL))
    batch.messages.append(batch.messages[0].model_copy(deep=True))
    keys = [r["case_key"] for r in batch.to_rows("f.xml")["cases"]]
    assert keys == ["f.xml#JP-DSJP-DSJ-2009-98765-1", "f.xml#JP-DSJP-DSJ-2009-98765-1[2]"]


def test_to_frames_without_pandas_is_a_clear_error(monkeypatch: pytest.MonkeyPatch) -> None:
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "pandas" or name.startswith("pandas."):
            raise ImportError("No module named 'pandas'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    with pytest.raises(ImportError, match=r"e2br3\[pandas\]"):
        e2br3.Batch().to_frames()


def test_shared_drug_id_is_exported_once_and_not_guessed() -> None:
    """KI-6: two G.k in FDA Scenario 5-3 share one id, so their G.k.9.i rows can't be attributed."""
    rows = e2br3.parse(require(FDA / "FAERS2022Scenario5-3.xml")).to_rows("s53.xml")
    ids = [d["drug_id"] for d in rows["drugs"]]
    shared = {i for i in ids if ids.count(i) > 1}
    assert len(shared) == 1
    ambiguous = [r for r in rows["drug_reaction"] if r["drug_id"] in shared]
    assert ambiguous and all(r["drug_index"] is None for r in ambiguous)
    assert all(r["drug_index"] is not None for r in rows["drug_reaction"] if r["drug_id"] not in shared)


def test_empty_batch_has_empty_tables() -> None:
    rows = e2br3.to_rows(e2br3.Batch(), "x")
    assert rows == {t: [] for t in TABLES}
