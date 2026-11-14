"""to-csv must not write text a spreadsheet would run as a formula (CSV injection).

ICSR files come from other organisations, so narrative, product and reporter text
is untrusted. Before the 2026-11-14 fix, a narrative starting with "=" was written
as-is and ran as a formula when the CSV was opened in Excel. JSON output, to_rows()
and to_frames() stay exact; only the CSV files are guarded, and --no-formula-guard
restores the old bytes.
"""
import csv
from pathlib import Path

import pytest

from e2br3 import cli
from e2br3.cli import _csv_safe, main
from e2br3.export import COLUMNS, TABLES


@pytest.mark.parametrize("raw", ['=HYPERLINK("http://x","y")', "+cmd|' /C calc'!A0", "-2+3", "@SUM(A1)",
                                 "\t=1+1", "\r=1+1"])
def test_formula_text_is_neutralised(raw):
    assert _csv_safe(raw) == "'" + raw


@pytest.mark.parametrize("value", ["-0.5", "+3", "-12.75", "1E+5", "plain text", "", None, 0, -5, True])
def test_numbers_and_ordinary_values_are_untouched(value):
    assert _csv_safe(value) == value


def _fake_rows(narrative):
    rows = {t: [] for t in TABLES}
    case = {c: None for c in COLUMNS["cases"]}
    case.update(narrative=narrative)
    rows["cases"].append(case)
    return rows


def _read_narrative(out_dir: Path):
    with (out_dir / "cases.csv").open(encoding="utf-8-sig", newline="") as fh:
        return next(csv.DictReader(fh))["narrative"]


@pytest.fixture
def crafted(monkeypatch):
    """Route to-csv through the real writer with one crafted case row."""
    payload = '=HYPERLINK("http://example.invalid","click")'
    monkeypatch.setattr(cli, "_load_all", lambda files: [("crafted.xml", object())])
    monkeypatch.setattr(cli, "to_rows", lambda batch, source: _fake_rows(payload))
    return payload


def test_to_csv_guards_by_default(crafted, tmp_path, capsys):
    assert main(["to-csv", "-o", str(tmp_path), "crafted.xml"]) == 0
    assert _read_narrative(tmp_path) == "'" + crafted


def test_no_formula_guard_restores_exact_text(crafted, tmp_path, capsys):
    assert main(["to-csv", "--no-formula-guard", "-o", str(tmp_path), "crafted.xml"]) == 0
    assert _read_narrative(tmp_path) == crafted
