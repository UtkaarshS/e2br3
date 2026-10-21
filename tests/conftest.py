"""Shared test paths and fixture-availability helpers.

The public sample files and the ICH XSD set are not committed (redistribution
terms unconfirmed). Fetch them with ``python scripts/fetch_fixtures.py``.
Tests that need them skip with a clear message when they are missing, e.g. on
CI without the fetch step.
"""
from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
SCHEMAS = ROOT / "schemas" / "ich-v2.5"
GOLDEN = ROOT / "tests" / "golden"

FETCH_HINT = "run `python scripts/fetch_fixtures.py` to download the public E2B(R3) samples"
SCHEMA_HINT = "ICH XSD set missing in schemas/ich-v2.5; run `python scripts/fetch_fixtures.py`"

FDA = FIXTURES / "fda"
EMA = FIXTURES / "ema"
ICH_EXAMPLES = FIXTURES / "ich-examples"
ICH_REFERENCE = FIXTURES / "ich-reference"

SCENARIO6 = FDA / "FAERS2022Scenario6.xml"
LIT_INITIAL = ICH_EXAMPLES / "1-1_ExampleCase_literature_initial_v1_0.xml"


def sample_xmls() -> list[Path]:
    """Every public sample XML present under tests/fixtures (ICSRs and the ICH ACK)."""
    if not FIXTURES.is_dir():
        return []
    return sorted(p for p in FIXTURES.rglob("*.xml") if p.is_file())


def full_sample_set() -> bool:
    """True when every sample source is present (FDA, EMA, ICH examples, ICH reference).

    On CI, fda.gov blocks the download, so usually only the EMA samples are there.
    Tests that count or enumerate the whole set use this to skip on a partial set.
    """
    return all(d.is_dir() and any(d.rglob("*.xml")) for d in (FDA, EMA, ICH_EXAMPLES, ICH_REFERENCE))


def is_ack(path: Path) -> bool:
    return "ACK" in path.name.upper()


def require(path: Path, hint: str = FETCH_HINT) -> Path:
    """Return ``path`` or skip the calling test if it does not exist."""
    if not path.exists():
        pytest.skip(f"fixture not found: {path.relative_to(ROOT)} ({hint})")
    return path


def require_schemas() -> Path:
    if not (SCHEMAS / "multicacheschemas" / "MCCI_IN200100UV01.xsd").is_file():
        pytest.skip(SCHEMA_HINT)
    return SCHEMAS


def params_or_skip(paths: list[Path], hint: str = FETCH_HINT) -> list:
    """pytest params for ``paths``, or a single skipped param when there are none."""
    if not paths:
        return [pytest.param(None, marks=pytest.mark.skip(reason=f"no sample fixtures ({hint})"), id="no-fixtures")]
    return [pytest.param(p, id=str(p.relative_to(FIXTURES)).replace("\\", "/")) for p in paths]
