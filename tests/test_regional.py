"""FR-8: regional elements (FDA.*, EU) are kept as raw key-value pass-through."""
from __future__ import annotations

from pathlib import Path

import pytest

import e2br3
from conftest import EMA, FDA, LIT_INITIAL, SCENARIO6, params_or_skip, require

FDA_FILES = sorted(FDA.glob("*.xml")) if FDA.is_dir() else []
NCI = "2.16.840.1.113883.3.26.1.1"


@pytest.mark.parametrize("path", params_or_skip(FDA_FILES))
def test_fda_scenarios_keep_fda_elements(path: Path) -> None:
    regional = e2br3.parse(path).messages[0].icsr.regional
    assert regional, "every FAERS2022 scenario carries FDA.* elements"
    assert all(k.startswith("FDA:") for k in regional)
    assert all(isinstance(v, str) for v in regional.values())


def test_scenario6_fda_values() -> None:
    regional = e2br3.parse(require(SCENARIO6)).messages[0].icsr.regional
    # FDA.D.11.r race (repeating, NCI Thesaurus codes) keeps every repeat in order
    races = [v for k, v in regional.items() if k.split("[")[0] == f"FDA:{NCI}:C17049"]
    assert races == ["C16352", "C41259", "C41260", "C41219", "C41261"]
    assert regional[f"FDA:{NCI}:C16564"] == "C17459"  # FDA.D.12 ethnicity
    assert regional[f"FDA:{NCI}:C156384"] == "true"  # FDA.C.1.12 combination product
    assert regional[f"FDA:{NCI}:C54588"] == "1"  # FDA.C.1.7.1 local criteria report type
    # nullFlavor on a regional element is passed through, not dropped
    assert regional["FDA:2.16.840.1.113883.3.989.5.1.2.2.1.3:7"] == "nullFlavor=NI"


def test_eu_elements_kept() -> None:
    regional = e2br3.parse(require(EMA / "01A. SE-EMA-TESTCASE01A.xml")).messages[0].icsr.regional
    assert regional and all(k.startswith("EU:") for k in regional)
    assert any("2.16.840.1.113883.3.989.5.1.1.5.2" in k for k in regional)  # EU method of assessment


def test_ich_only_case_has_no_regional_elements() -> None:
    assert e2br3.parse(require(LIT_INITIAL)).messages[0].icsr.regional == {}
