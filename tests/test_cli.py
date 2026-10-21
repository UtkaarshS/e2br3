"""FR-7: the e2br3 CLI (validate | show | to-json | to-csv), via main(argv) and as a subprocess."""
from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import e2br3
from e2br3.cli import main
from e2br3.export import COLUMNS, TABLES
from conftest import EMA, FDA, LIT_INITIAL, ROOT, SCHEMAS, SCENARIO6, require, require_schemas

EMA10 = EMA / "10. ES-EMA-TESTCASE10.xml"  # a path with spaces and dots
ACK = FDA / "R3ack-positive.ack"


def run(capsys: pytest.CaptureFixture[str], *argv: str) -> tuple[int, str, str]:
    code = main(list(argv))
    out, err = capsys.readouterr()
    return code, out, err


# --------------------------------------------------------------------------- validate


def test_validate_ok(capsys) -> None:
    require_schemas()
    code, out, _ = run(capsys, "validate", str(require(LIT_INITIAL)), str(require(EMA10)))
    assert code == 0
    assert out.splitlines()[0].startswith("OK ")
    assert "2 of 2 file(s) valid" in out


def test_validate_bad_file_exits_1_with_line_numbers(capsys, tmp_path: Path) -> None:
    require_schemas()
    text = require(LIT_INITIAL).read_text(encoding="utf-8")
    old = '<responseModeCode code="D"/>'
    bad = tmp_path / "bad case.xml"
    bad.write_text(text.replace(old, old + "<bogusElement/>"), encoding="utf-8")
    line = next(i for i, ln in enumerate(bad.read_text(encoding="utf-8").splitlines(), 1) if "bogusElement" in ln)
    code, out, err = run(capsys, "validate", "--schema-dir", str(SCHEMAS), str(LIT_INITIAL), str(bad))
    assert code == 1
    assert "INVALID" in out and f"{bad}:{line}:" in out and "bogusElement" in out
    assert "Traceback" not in out + err


def test_validate_missing_file_is_reported_not_raised(capsys, tmp_path: Path) -> None:
    require_schemas()
    code, out, err = run(capsys, "validate", str(tmp_path / "nope.xml"))
    assert code == 1 and "no such file" in out and "Traceback" not in err


def test_validate_missing_schema_dir_exits_2(capsys, tmp_path: Path) -> None:
    code, _, err = run(capsys, "validate", "--schema-dir", str(tmp_path), str(require(LIT_INITIAL)))
    assert code == 2 and "XSD set" in err and "--schema-dir" in err


# --------------------------------------------------------------------------- show


def test_show_summary(capsys) -> None:
    code, out, _ = run(capsys, "show", str(require(LIT_INITIAL)))
    assert code == 0
    assert "C.1.1  JP-DSJP-DSJ-2009-98765-1" in out
    assert "Report type  1 (spontaneous report)" in out
    assert "sex 2 (female), age 81 a" in out
    assert "Reactions (1)" in out and "10022617" in out
    assert "MEVALOTIN (suspect)" in out
    assert "Serious  yes:" in out and "life threatening" in out


def test_show_nullflavor_is_visible(capsys) -> None:
    code, out, _ = run(capsys, "show", str(require(EMA10)))
    assert code == 0 and str(EMA10) in out


def test_show_ack_is_a_clean_error(capsys) -> None:
    code, out, err = run(capsys, "show", str(require(ACK)))
    assert code == 1
    assert err.startswith("e2br3: error:") and "acknowledgement" in err
    assert "Traceback" not in err


def test_show_not_xml_is_a_clean_error(capsys, tmp_path: Path) -> None:
    junk = tmp_path / "junk.xml"
    junk.write_text("this is not xml", encoding="utf-8")
    code, _, err = run(capsys, "show", str(junk))
    assert code == 1 and "well-formed" in err and "Traceback" not in err


def test_show_missing_file(capsys, tmp_path: Path) -> None:
    code, _, err = run(capsys, "show", str(tmp_path / "missing.xml"))
    assert code == 1 and "cannot read file" in err


# --------------------------------------------------------------------------- to-json


def test_to_json_stdout(capsysbinary) -> None:
    path = require(EMA10)
    assert main(["to-json", str(path)]) == 0
    out = capsysbinary.readouterr().out.decode("utf-8")
    data = json.loads(out)
    assert data == e2br3.parse(path).to_dict()
    assert data["messages"][0]["icsr"]["patient"]["name"] == {"nullFlavor": "UNK"}


def test_to_json_file_with_several_inputs(capsys, tmp_path: Path) -> None:
    out_file = tmp_path / "out dir" / "all.json"
    out_file.parent.mkdir()
    files = [str(require(LIT_INITIAL)), str(require(SCENARIO6))]
    code, out, _ = run(capsys, "to-json", "-o", str(out_file), *files)
    assert code == 0 and out == ""
    data = json.loads(out_file.read_text(encoding="utf-8"))
    assert [d["file"] for d in data] == files
    assert e2br3.Batch.model_validate(data[0]["batch"]).messages[0].icsr.safety_report_id == "JP-DSJP-DSJ-2009-98765-1"
    assert "間質性肺炎" in out_file.read_text(encoding="utf-8")  # UTF-8, not \u-escaped


def test_to_json_writes_nothing_if_any_input_fails(capsys, tmp_path: Path) -> None:
    out_file = tmp_path / "x.json"
    code, _, err = run(capsys, "to-json", "-o", str(out_file), str(require(LIT_INITIAL)), str(tmp_path / "missing.xml"))
    assert code == 1 and not out_file.exists() and "missing.xml" in err


# --------------------------------------------------------------------------- to-csv


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def test_to_csv_tables(capsys, tmp_path: Path) -> None:
    files = [require(LIT_INITIAL), require(SCENARIO6), require(EMA10)]
    out_dir = tmp_path / "csv out"
    code, out, _ = run(capsys, "to-csv", "-o", str(out_dir), *map(str, files))
    assert code == 0 and "wrote 4 CSV files" in out
    expected = {t: [] for t in TABLES}
    for f in files:
        for t, rows in e2br3.parse(f).to_rows(str(f)).items():
            expected[t].extend(rows)
    for t in TABLES:
        rows = _read_csv(out_dir / f"{t}.csv")
        assert len(rows) == len(expected[t]), t
        assert tuple(rows[0]) == COLUMNS[t]
    cases = _read_csv(out_dir / "cases.csv")
    assert cases[0]["case_key"] == f"{LIT_INITIAL}#JP-DSJP-DSJ-2009-98765-1"
    assert cases[2]["patient_name"] == "nullFlavor=UNK"
    reactions = _read_csv(out_dir / "reactions.csv")
    assert reactions[0]["native_term"] == "間質性肺炎"


def test_to_csv_expands_globs(capsys, tmp_path: Path) -> None:
    """cmd.exe and PowerShell don't expand wildcards, so the CLI does."""
    require(SCENARIO6)
    code, out, _ = run(capsys, "to-csv", "-o", str(tmp_path), str(FDA / "FAERS2022Scenario*.xml"))
    assert code == 0
    assert len(_read_csv(tmp_path / "cases.csv")) == len(list(FDA.glob("FAERS2022Scenario*.xml")))


def test_to_csv_requires_output_dir(capsys) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["to-csv", "x.xml"])
    assert exc.value.code == 2


# --------------------------------------------------------------------------- python -m e2br3


def _python_m(*argv: str) -> subprocess.CompletedProcess[bytes]:
    env = dict(os.environ, PYTHONPATH=str(ROOT / "src"))
    return subprocess.run([sys.executable, "-m", "e2br3", *argv], capture_output=True, env=env, cwd=ROOT, timeout=120)


def test_python_m_show_subprocess() -> None:
    proc = _python_m("show", str(require(LIT_INITIAL)))
    assert proc.returncode == 0, proc.stderr
    # stdout is a pipe (cp1252 on Windows): unencodable text is escaped, never a crash
    assert b"JP-DSJP-DSJ-2009-98765-1" in proc.stdout


def test_python_m_to_json_is_utf8_on_a_pipe() -> None:
    proc = _python_m("to-json", str(require(LIT_INITIAL)))
    assert proc.returncode == 0, proc.stderr
    assert "間質性肺炎" in json.loads(proc.stdout.decode("utf-8"))["messages"][0]["icsr"]["reactions"][0]["native_term"]


def test_python_m_error_has_no_traceback(tmp_path: Path) -> None:
    proc = _python_m("to-json", str(tmp_path / "missing.xml"))
    assert proc.returncode == 1
    assert b"Traceback" not in proc.stderr and b"e2br3: error:" in proc.stderr


def test_python_m_version() -> None:
    proc = _python_m("--version")
    assert proc.returncode == 0 and e2br3.__version__.encode() in proc.stdout
