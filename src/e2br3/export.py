"""FR-6 export: JSON-safe dicts, JSON text and four tidy tables.

``to_dict()`` / ``to_json()`` dump the whole model tree. A nullFlavor is
exported as ``{"nullFlavor": "UNK"}`` and an absent element as ``null``, so the
two never collapse; ``Batch.model_validate_json(to_json(batch)) == batch``.

``to_rows()`` flattens one :class:`~e2br3.models.Batch` into four tables, each a
list of flat dicts, without needing pandas. ``to_frames()`` wraps the same rows
in pandas DataFrames (optional ``pandas`` extra, imported lazily).

Tables (one row per ...):

``cases``          ICSR (N.2.r message)
``reactions``      E.i reaction
``drugs``          G.k drug
``drug_reaction``  G.k.9.i.2.r relatedness assessment (drug x reaction x assessment)

Every table starts with ``case_key``: ``"<source>#<C.1.1>"``, where ``source``
names the batch file (pass it in; it defaults to N.1.2 batch number) and a C.1.1
repeated inside one batch gets a ``[2]``, ``[3]`` ... suffix.

Cell values are flat: a coded value becomes its code, a date its raw HL7 TS
string, a quantity its number as text, a nullFlavor the string
``"nullFlavor=UNK"`` and an absent element ``None``.
"""
from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any, Optional

from .models import TS, Batch, Coded, Quantity
from .nullflavor import Null

if TYPE_CHECKING:  # pragma: no cover
    import pandas as pd

TABLES = ("cases", "reactions", "drugs", "drug_reaction")

SERIOUSNESS = (
    "results_in_death",
    "life_threatening",
    "hospitalisation",
    "disabling",
    "congenital_anomaly",
    "other_medically_important",
)

COLUMNS: dict[str, tuple[str, ...]] = {
    "cases": (
        "case_key", "source", "message_index", "safety_report_id", "worldwide_case_id",
        "creation_date", "report_type", "first_received_date", "most_recent_date",
        "nullification_amendment", "primary_source_country", "primary_source_qualification",
        "patient_name", "patient_age", "patient_age_unit", "patient_sex",
        "serious", "reaction_count", "drug_count", "narrative",
    ),
    "reactions": (
        "case_key", "reaction_index", "reaction_id", "native_term", "native_language",
        "translated_term", "meddra_code", "meddra_version", "start_date", "end_date",
        *SERIOUSNESS, "outcome",
    ),
    "drugs": (
        "case_key", "drug_index", "drug_id", "role", "product_name", "substances",
        "dosage_text", "route_text", "route", "action_taken",
    ),
    "drug_reaction": (
        "case_key", "drug_index", "drug_id", "reaction_index", "reaction_id",
        "assessment_index", "source", "method", "result",
    ),
}

#: Separator used when a repeating sub-element (substances, dosages) is put in one cell.
JOIN = "; "


def to_dict(obj: Any) -> dict[str, Any]:
    """JSON-safe dict of any e2br3 model (``obj.to_dict()``)."""
    return obj.model_dump(mode="json", by_alias=True)


def to_json(obj: Any, indent: Optional[int] = None) -> str:
    """JSON text of any e2br3 model (``obj.to_json()``)."""
    return obj.model_dump_json(by_alias=True, indent=indent)


def cell(v: Any) -> Any:
    """Reduce a parsed value to one flat, CSV- and JSON-safe cell."""
    if v is None or isinstance(v, (bool, int, str)):
        return v
    if isinstance(v, Null):
        return str(v)  # "nullFlavor=UNK"
    if isinstance(v, Coded):
        return v.code if v.code is not None else v.original_text
    if isinstance(v, TS):
        return v.raw
    if isinstance(v, Decimal):
        return format(v, "f")
    return str(v)


def _joined(values: list[Any]) -> Optional[str]:
    cells = [cell(v) for v in values]
    present = [str(c) for c in cells if c is not None]
    return JOIN.join(present) if present else None


def _serious(reactions: list[Any]) -> Optional[bool]:
    """True if any reaction has a seriousness criterion true; False if some are false and none true."""
    flags = [getattr(r, name) for r in reactions for name in SERIOUSNESS]
    if any(f is True for f in flags):
        return True
    if any(f is False for f in flags):
        return False
    return None


def to_rows(batch: Batch, source: Optional[str] = None) -> dict[str, list[dict[str, Any]]]:
    """Flatten ``batch`` into the four tables (see the module docstring)."""
    if source is None:
        source = str(cell(batch.batch_number) or "")
    rows: dict[str, list[dict[str, Any]]] = {t: [] for t in TABLES}
    seen: dict[str, int] = {}
    for m_idx, msg in enumerate(batch.messages):
        icsr = msg.icsr
        if icsr is None:
            continue
        key = f"{source}#{cell(icsr.safety_report_id) or ''}"
        seen[key] = seen.get(key, 0) + 1
        if seen[key] > 1:
            key = f"{key}[{seen[key]}]"

        patient = icsr.patient
        age = patient.age if patient is not None else None
        src = icsr.primary_sources[0] if icsr.primary_sources else None
        rows["cases"].append({
            "case_key": key,
            "source": source,
            "message_index": m_idx,
            "safety_report_id": cell(icsr.safety_report_id),
            "worldwide_case_id": cell(icsr.worldwide_case_id),
            "creation_date": cell(icsr.creation_date),
            "report_type": cell(icsr.report_type),
            "first_received_date": cell(icsr.first_received_date),
            "most_recent_date": cell(icsr.most_recent_date),
            "nullification_amendment": cell(icsr.nullification_amendment),
            "primary_source_country": cell(src.country) if src else None,
            "primary_source_qualification": cell(src.qualification) if src else None,
            "patient_name": cell(patient.name) if patient else None,
            "patient_age": cell(age.value) if isinstance(age, Quantity) else cell(age),
            "patient_age_unit": age.unit if isinstance(age, Quantity) else None,
            "patient_sex": cell(patient.sex) if patient else None,
            "serious": _serious(icsr.reactions),
            "reaction_count": len(icsr.reactions),
            "drug_count": len(icsr.drugs),
            "narrative": cell(icsr.narrative),
        })

        for r_idx, rx in enumerate(icsr.reactions):
            meddra = rx.meddra
            rows["reactions"].append({
                "case_key": key,
                "reaction_index": r_idx,
                "reaction_id": rx.id,
                "native_term": cell(rx.native_term),
                "native_language": rx.native_language,
                "translated_term": cell(rx.translated_term),
                "meddra_code": cell(meddra),
                "meddra_version": meddra.code_system_version if isinstance(meddra, Coded) else None,
                "start_date": cell(rx.start_date),
                "end_date": cell(rx.end_date),
                **{name: cell(getattr(rx, name)) for name in SERIOUSNESS},
                "outcome": cell(rx.outcome),
            })

        # G.k.9.i points at a drug by id. If several G.k share one id (a sample
        # defect, KI-6) the parser gives each of them the same matrix; emit each
        # assessment once and leave drug_index unset rather than guess.
        by_id: dict[Optional[str], list[int]] = {}
        for d_idx, drug in enumerate(icsr.drugs):
            by_id.setdefault(drug.id, []).append(d_idx)

        for d_idx, drug in enumerate(icsr.drugs):
            rows["drugs"].append({
                "case_key": key,
                "drug_index": d_idx,
                "drug_id": drug.id,
                "role": cell(drug.role),
                "product_name": cell(drug.product_name),
                "substances": _joined(drug.substances),
                "dosage_text": _joined([d.text for d in drug.dosages]),
                "route_text": _joined([d.route_text for d in drug.dosages]),
                "route": _joined([d.route for d in drug.dosages]),
                "action_taken": cell(drug.action_taken),
            })
            owners = by_id.get(drug.id, [d_idx])
            if owners[0] != d_idx:
                continue  # same id as an earlier drug: its assessments are already out
            for dr in drug.relatedness:
                for a_idx, a in enumerate(dr.assessments):
                    rows["drug_reaction"].append({
                        "case_key": key,
                        "drug_index": d_idx if len(owners) == 1 else None,
                        "drug_id": drug.id,
                        "reaction_index": dr.reaction_index,
                        "reaction_id": dr.reaction_id,
                        "assessment_index": a_idx,
                        "source": cell(a.source),
                        "method": cell(a.method),
                        "result": cell(a.result),
                    })
    return rows


def to_frames(batch: Batch, source: Optional[str] = None) -> "dict[str, pd.DataFrame]":
    """The four tables of :func:`to_rows` as pandas DataFrames (needs ``pip install e2br3[pandas]``)."""
    try:
        import pandas as pd
    except ImportError as exc:
        raise ImportError(
            "to_frames() needs pandas, which is an optional extra: pip install 'e2br3[pandas]'. "
            "to_rows() returns the same tables as lists of dicts without pandas."
        ) from exc
    rows = to_rows(batch, source)
    return {t: pd.DataFrame(rows[t], columns=list(COLUMNS[t])) for t in TABLES}
