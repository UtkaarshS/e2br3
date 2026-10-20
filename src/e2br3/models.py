"""Typed E2B(R3) models for the v0.1 core subset (SRS FR-2, FR-3, FR-4).

Shape: :class:`Batch` (N.1) -> :class:`Message` (N.2.r) -> :class:`ICSR`.

Field conventions:

* Every data element is ``Nullable[X]``: an ``X``, a :class:`~e2br3.nullflavor.Null`
  or ``None`` (absent). See :mod:`e2br3.nullflavor`.
* Coded values (MedDRA, ICH code lists, ISO 3166, EDQM ...) are stored as
  :class:`Coded`: code + code-system OID + version + displayName as sent.
  No dictionary lookup is done and none is bundled.
* Dates are :class:`TS`: the raw HL7 TS string plus a precision-aware value.
* Each field's description starts with its ICH data-element ID.
"""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field

from .nullflavor import Nullable

Precision = Literal["year", "month", "day", "hour", "minute", "second", "fraction"]

_TS_RE = re.compile(
    r"^(?P<y>\d{4})(?P<mo>\d{2})?(?P<d>\d{2})?(?P<h>\d{2})?(?P<mi>\d{2})?(?P<s>\d{2})?"
    r"(?:\.(?P<f>\d{1,6}))?(?P<tz>[+-]\d{2}(?:\d{2})?)?$"
)


class _Model(BaseModel):
    model_config = ConfigDict(frozen=False, extra="forbid")


class Coded(_Model):
    """A coded value (HL7 CE/CD) kept exactly as sent; never looked up."""

    code: Optional[str] = None
    code_system: Optional[str] = Field(None, description="Code-system OID")
    code_system_version: Optional[str] = None
    display_name: Optional[str] = None
    original_text: Optional[str] = None


class TS(_Model):
    """HL7 TS point in time, ``CCYY[MM[DD[hh[mm[ss[.UUUU]]]]]][+|-ZZzz]``: raw string plus parsed value.

    ``value`` is a ``date`` for year/month/day precision (missing parts filled
    with 1; read ``precision`` before trusting them) and a ``datetime`` for
    hour precision or finer. It is ``None`` if the raw string is not a valid TS.
    """

    raw: str
    precision: Optional[Precision] = None
    value: Optional[Union[datetime, date]] = None
    tz_offset: Optional[str] = Field(None, description="Offset as sent, e.g. '+09' or '-0500'")

    @classmethod
    def from_hl7(cls, raw: str) -> "TS":
        m = _TS_RE.match(raw.strip())
        if not m:
            return cls(raw=raw)
        g = m.groupdict()
        order = ["y", "mo", "d", "h", "mi", "s", "f"]
        names: list[Precision] = ["year", "month", "day", "hour", "minute", "second", "fraction"]
        precision: Precision = "year"
        for key, name in zip(order, names):
            if g[key] is None:
                break
            precision = name
        try:
            y, mo, d = int(g["y"]), int(g["mo"] or 1), int(g["d"] or 1)
            if g["h"] is None:
                value: Union[date, datetime] = date(y, mo, d)
            else:
                tzinfo = None
                if g["tz"]:
                    sign = -1 if g["tz"][0] == "-" else 1
                    hh, mm = int(g["tz"][1:3]), int(g["tz"][3:5] or 0)
                    tzinfo = timezone(sign * timedelta(hours=hh, minutes=mm))
                micro = int((g["f"] or "0").ljust(6, "0"))
                value = datetime(
                    y, mo, d, int(g["h"]), int(g["mi"] or 0), int(g["s"] or 0), micro, tzinfo=tzinfo
                )
        except ValueError:
            return cls(raw=raw, precision=precision)
        return cls(raw=raw, precision=precision, value=value, tz_offset=g["tz"])


class Quantity(_Model):
    """HL7 PQ: a number and a UCUM unit, as sent."""

    value: Optional[Decimal] = None
    unit: Optional[str] = None


class Attachment(_Model):
    """HL7 ED with base64 or text content, passed through untouched."""

    media_type: Optional[str] = None
    representation: Optional[str] = None
    data: Optional[str] = None


# --------------------------------------------------------------------------- C.2.r / C.4.r


class PrimarySource(_Model):
    """C.2.r Primary source of information (core subset only)."""

    country: Nullable[Coded] = Field(None, description="C.2.r.3 Reporter's country code (ISO 3166-1)")
    qualification: Nullable[Coded] = Field(None, description="C.2.r.4 Qualification")


class Literature(_Model):
    """C.4.r Literature reference."""

    reference: Nullable[str] = Field(None, description="C.4.r.1 Literature reference(s)")
    document: Nullable[Attachment] = Field(None, description="C.4.r.2 Included documents")


# --------------------------------------------------------------------------- D / E.i / G.k


class Patient(_Model):
    """D Patient characteristics (core subset only)."""

    name: Nullable[str] = Field(None, description="D.1 Patient (name or initials)")
    age: Nullable[Quantity] = Field(None, description="D.2.2a/b Age at time of onset (number, unit)")
    sex: Nullable[Coded] = Field(None, description="D.5 Sex (ISO 5218)")


class Reaction(_Model):
    """E.i Reaction / event."""

    id: Optional[str] = Field(None, description="Internal id used by G.k.9.i cross-references")
    native_term: Nullable[str] = Field(None, description="E.i.1.1a Reaction as reported, native language")
    native_language: Optional[str] = Field(None, description="E.i.1.1b Language of E.i.1.1a")
    translated_term: Nullable[str] = Field(None, description="E.i.1.2 Reaction as reported, for translation")
    meddra: Nullable[Coded] = Field(None, description="E.i.2.1a/b MedDRA version and LLT code")
    start_date: Nullable[TS] = Field(None, description="E.i.4 Date of start of reaction")
    end_date: Nullable[TS] = Field(None, description="E.i.5 Date of end of reaction")
    results_in_death: Nullable[bool] = Field(None, description="E.i.3.2a Results in death")
    life_threatening: Nullable[bool] = Field(None, description="E.i.3.2b Life threatening")
    hospitalisation: Nullable[bool] = Field(None, description="E.i.3.2c Caused / prolonged hospitalisation")
    disabling: Nullable[bool] = Field(None, description="E.i.3.2d Disabling / incapacitating")
    congenital_anomaly: Nullable[bool] = Field(None, description="E.i.3.2e Congenital anomaly / birth defect")
    other_medically_important: Nullable[bool] = Field(None, description="E.i.3.2f Other medically important")
    outcome: Nullable[Coded] = Field(None, description="E.i.7 Outcome at time of last observation")

    @property
    def meddra_code(self) -> Optional[str]:
        return self.meddra.code if isinstance(self.meddra, Coded) else None

    @property
    def meddra_version(self) -> Optional[str]:
        return self.meddra.code_system_version if isinstance(self.meddra, Coded) else None


class Dosage(_Model):
    """G.k.4.r Dosage and relevant information (core subset only)."""

    text: Nullable[str] = Field(None, description="G.k.4.r.8 Dosage text")
    route_text: Nullable[str] = Field(None, description="G.k.4.r.10.1 Route of administration (free text)")
    route: Nullable[Coded] = Field(None, description="G.k.4.r.10.2a/b Route of administration TermID")


class Assessment(_Model):
    """G.k.9.i.2.r Assessment of relatedness of drug to reaction."""

    source: Nullable[Coded] = Field(None, description="G.k.9.i.2.r.1 Source of assessment")
    method: Nullable[Coded] = Field(None, description="G.k.9.i.2.r.2 Method of assessment")
    result: Nullable[Union[Coded, str]] = Field(None, description="G.k.9.i.2.r.3 Result of assessment")


class DrugReaction(_Model):
    """G.k.9.i Drug-reaction matrix entry (relatedness only)."""

    reaction_id: Optional[str] = Field(None, description="G.k.9.i.1 Reaction assessed (internal id)")
    reaction_index: Optional[int] = Field(
        None, description="Index into ICSR.reactions of the referenced reaction; None if unresolved"
    )
    assessments: list[Assessment] = Field(default_factory=list)


class Drug(_Model):
    """G.k Drug information (core subset only)."""

    id: Optional[str] = Field(None, description="Internal id used by G.k.1 and G.k.9.i cross-references")
    role: Nullable[Coded] = Field(None, description="G.k.1 Characterisation of drug role")
    product_name: Nullable[str] = Field(None, description="G.k.2.2 Medicinal product name as reported")
    substances: list[Nullable[str]] = Field(
        default_factory=list, description="G.k.2.3.r.1 Substance / specified substance name"
    )
    dosages: list[Dosage] = Field(default_factory=list, description="G.k.4.r")
    action_taken: Nullable[Coded] = Field(None, description="G.k.8 Action(s) taken with drug")
    relatedness: list[DrugReaction] = Field(default_factory=list, description="G.k.9.i")


# --------------------------------------------------------------------------- ICSR / N.2.r / N.1


class ICSR(_Model):
    """One case safety report (the investigationEvent)."""

    safety_report_id: Nullable[str] = Field(None, description="C.1.1 Sender's safety report unique id")
    creation_date: Nullable[TS] = Field(None, description="C.1.2 Date of creation")
    report_type: Nullable[Coded] = Field(None, description="C.1.3 Type of report")
    first_received_date: Nullable[TS] = Field(None, description="C.1.4 Date first received from source")
    most_recent_date: Nullable[TS] = Field(None, description="C.1.5 Date of most recent information")
    worldwide_case_id: Nullable[str] = Field(None, description="C.1.8.1 Worldwide unique case id")
    nullification_amendment: Nullable[Coded] = Field(None, description="C.1.11.1 Nullification / amendment")
    nullification_reason: Nullable[str] = Field(None, description="C.1.11.2 Reason for nullification / amendment")
    primary_sources: list[PrimarySource] = Field(default_factory=list, description="C.2.r")
    literature: list[Literature] = Field(default_factory=list, description="C.4.r")
    patient: Optional[Patient] = Field(None, description="D")
    reactions: list[Reaction] = Field(default_factory=list, description="E.i")
    drugs: list[Drug] = Field(default_factory=list, description="G.k")
    narrative: Nullable[str] = Field(None, description="H.1 Case narrative")
    regional: dict[str, str] = Field(
        default_factory=dict, description="FR-8: FDA.* / EU regional elements, raw key-value pass-through"
    )


class Message(_Model):
    """N.2.r Message header (PORR_IN049016UV)."""

    message_id: Nullable[str] = Field(None, description="N.2.r.1 Message identifier")
    sender: Nullable[str] = Field(None, description="N.2.r.2 Message sender identifier")
    receiver: Nullable[str] = Field(None, description="N.2.r.3 Message receiver identifier")
    creation_date: Nullable[TS] = Field(None, description="N.2.r.4 Date of message creation")
    icsr: Optional[ICSR] = None


class Batch(_Model):
    """N.1 Batch wrapper (MCCI_IN200100UV01)."""

    batch_type: Nullable[Coded] = Field(None, description="N.1.1 Type of messages in batch")
    batch_number: Nullable[str] = Field(None, description="N.1.2 Batch number")
    sender: Nullable[str] = Field(None, description="N.1.3 Batch sender identifier")
    receiver: Nullable[str] = Field(None, description="N.1.4 Batch receiver identifier")
    transmission_date: Nullable[TS] = Field(None, description="N.1.5 Date of batch transmission")
    messages: list[Message] = Field(default_factory=list, description="N.2.r")

    @property
    def icsrs(self) -> list[ICSR]:
        return [m.icsr for m in self.messages if m.icsr is not None]
