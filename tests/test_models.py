"""Unit tests for the value types (no fixtures needed)."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest

from e2br3 import TS


@pytest.mark.parametrize(
    "raw, precision, value",
    [
        ("2008", "year", date(2008, 1, 1)),
        ("200807", "month", date(2008, 7, 1)),
        ("20081009", "day", date(2008, 10, 9)),
        ("2012072010", "hour", datetime(2012, 7, 20, 10)),
        ("201207201030", "minute", datetime(2012, 7, 20, 10, 30)),
        ("20120720100000", "second", datetime(2012, 7, 20, 10, 0, 0)),
        ("20120720100000.12", "fraction", datetime(2012, 7, 20, 10, 0, 0, 120000)),
    ],
)
def test_ts_precision(raw: str, precision: str, value) -> None:
    ts = TS.from_hl7(raw)
    assert ts.raw == raw and ts.precision == precision and ts.value == value
    assert type(ts.value) is type(value)


def test_ts_timezones() -> None:
    a = TS.from_hl7("20120720100001+09")
    assert a.value == datetime(2012, 7, 20, 10, 0, 1, tzinfo=timezone(timedelta(hours=9)))
    assert a.tz_offset == "+09"
    b = TS.from_hl7("20220614101010-0500")
    assert b.value.utcoffset() == timedelta(hours=-5)


@pytest.mark.parametrize("raw", ["2003-05-11", "20081301", "abc", ""])
def test_invalid_ts_keeps_raw(raw: str) -> None:
    ts = TS.from_hl7(raw)
    assert ts.raw == raw and ts.value is None


def test_ts_json_round_trip() -> None:
    for raw in ["2008", "20120720100001+09"]:
        ts = TS.from_hl7(raw)
        assert TS.model_validate_json(ts.model_dump_json()) == ts
