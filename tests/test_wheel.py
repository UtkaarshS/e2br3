"""Licensing guard on the built distributions (run `uv build` first; skipped otherwise).

test_security.py checks the source package directory. This checks what would
actually ship: the wheel and the sdist in dist/ must hold code only, with no
sample files, ICH schemas or dictionary files (MedDRA forbids redistribution).
"""
from __future__ import annotations

import re
import tarfile
import zipfile
from pathlib import Path

import pytest

import e2br3
from conftest import ROOT

DIST = ROOT / "dist"
VERSION = e2br3.__version__
FORBIDDEN = re.compile(
    r"(meddra|mdhier|llt|hlgt|edqm|whodrug|snomed|fixtures|schemas|golden|\.xml$|\.xsd$|\.ack$"
    r"|\.asc$|\.csv$|\.xlsx?$|\.zip$|\.db$|\.sqlite$|\.json$)",
    re.IGNORECASE,
)


def _one(pattern: str) -> Path:
    found = sorted(DIST.glob(pattern)) if DIST.is_dir() else []
    if not found:
        pytest.skip(f"no {pattern} in dist/ (run `uv build` first)")
    return found[-1]


def test_wheel_contains_code_only() -> None:
    wheel = _one(f"e2br3-{VERSION}-*.whl")
    names = zipfile.ZipFile(wheel).namelist()
    dist_info = f"e2br3-{VERSION}.dist-info/"
    code = [n for n in names if not n.startswith(dist_info)]
    assert code and all(n.startswith("e2br3/") and n.endswith(".py") for n in code), code
    assert {n[len(dist_info):] for n in names if n.startswith(dist_info)} <= {
        "METADATA", "WHEEL", "RECORD", "entry_points.txt", "licenses/LICENSE",
    }
    for n in names:
        assert not FORBIDDEN.search(n), n


def test_wheel_metadata() -> None:
    wheel = zipfile.ZipFile(_one(f"e2br3-{VERSION}-*.whl"))
    meta = wheel.read(f"e2br3-{VERSION}.dist-info/METADATA").decode("utf-8")
    requires = sorted(line.split(":", 1)[1].strip() for line in meta.splitlines() if line.startswith("Requires-Dist:"))
    assert requires == ["lxml>=4.9", "pandas>=2; extra == 'pandas'", "pydantic>=2"]
    assert "e2br3 = e2br3.cli:main" in wheel.read(f"e2br3-{VERSION}.dist-info/entry_points.txt").decode("utf-8")


def test_sdist_contains_no_fixtures_or_schemas() -> None:
    sdist = _one(f"e2br3-{VERSION}.tar.gz")
    with tarfile.open(sdist) as tf:
        names = [n.split("/", 1)[1] for n in tf.getnames() if "/" in n]
    assert names
    for n in names:
        assert not FORBIDDEN.search(n), n
        assert n.split("/")[0] in {"src", "README.md", "CHANGELOG.md", "LICENSE", "pyproject.toml", ".gitignore", "PKG-INFO"}, n
