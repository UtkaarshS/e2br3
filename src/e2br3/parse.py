"""``parse()``: E2B(R3) batch XML -> :class:`~e2br3.models.Batch` (SRS FR-1..FR-4, FR-8).

The reading rules live in :mod:`e2br3.mapping`; this module only walks the
context nodes, applies the table and resolves the internal cross-references
(G.k.1 and G.k.9.i point at drugs and reactions by ``II`` id).
"""
from __future__ import annotations

import os
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Callable, Optional, Union

from lxml import etree

from .mapping import MAPPING, NS, REGIONAL_ARCS
from .models import (
    TS,
    Assessment,
    Attachment,
    Batch,
    Coded,
    Dosage,
    Drug,
    DrugReaction,
    ICSR,
    Literature,
    Message,
    Patient,
    PrimarySource,
    Quantity,
    Reaction,
)
from .nullflavor import Null, NullFlavor

HL7_NS = NS["h"]
BATCH_ROOT = "MCCI_IN200100UV01"

Source = Union[str, "os.PathLike[str]", bytes]


class E2BParseError(ValueError):
    """The input is not a parseable E2B(R3) ICSR batch."""


def make_parser() -> etree.XMLParser:
    """An XXE-safe lxml parser: no entity expansion, no DTD loading, no network."""
    return etree.XMLParser(
        resolve_entities=False,
        no_network=True,
        load_dtd=False,
        dtd_validation=False,
        huge_tree=False,
    )


def has_dtd(tree: etree._ElementTree) -> bool:
    """True if the document carries a DOCTYPE (internal subset or external DTD)."""
    info = tree.docinfo
    return bool(info.doctype) or info.internalDTD is not None or bool(info.system_url)


def load_tree(source: Source) -> etree._ElementTree:
    """Parse ``source`` (a path or the XML bytes) safely into an lxml tree.

    Two layers of protection: the parser never loads external entities, DTDs or
    network resources, and any document with a DOCTYPE is refused outright.
    E2B(R3) instances are XSD-based and never need a DTD, and refusing them also
    stops internal-entity expansion ("billion laughs") when text is read later.
    """
    parser = make_parser()
    try:
        if isinstance(source, (bytes, bytearray)):
            tree = etree.ElementTree(etree.fromstring(bytes(source), parser))
        else:
            tree = etree.parse(str(Path(source)), parser)
    except etree.XMLSyntaxError as exc:
        raise E2BParseError(f"not well-formed XML: {exc}") from exc
    if has_dtd(tree):
        raise E2BParseError("document type declarations (DTD) are not allowed in E2B(R3) XML; refused")
    return tree


# --------------------------------------------------------------------------- readers

_XPATH = {eid: etree.XPath(el.xpath, namespaces=NS) for eid, el in MAPPING.items()}
_STRING = etree.XPath("string()")
_ORIGINAL_TEXT = etree.XPath("h:originalText", namespaces=NS)
_VALUE = etree.XPath("h:value", namespaces=NS)


def _text(node: Any) -> str:
    return str(_STRING(node))


def _original_text(node: Any) -> Optional[str]:
    found = _ORIGINAL_TEXT(node)
    return _text(found[0]) if found else None


def _coded(node: Any) -> Coded:
    return Coded(
        code=node.get("code"),
        code_system=node.get("codeSystem"),
        code_system_version=node.get("codeSystemVersion"),
        display_name=node.get("displayName"),
        original_text=_original_text(node),
    )


def _bool(node: Any) -> Optional[bool]:
    v = node.get("value")
    if v == "true":
        return True
    if v == "false":
        return False
    return None


def _pq(node: Any) -> Quantity:
    raw = node.get("value")
    value: Optional[Decimal] = None
    if raw is not None:
        try:
            value = Decimal(raw)
        except InvalidOperation:
            value = None
    return Quantity(value=value, unit=node.get("unit"))


def _ref(node: Any) -> Optional[str]:
    root, ext = node.get("root"), node.get("extension")
    if root is None:
        return ext
    return f"{root}|{ext}" if ext else root


def _ts(node: Any) -> Optional[TS]:
    v = node.get("value")
    return TS.from_hl7(v) if v is not None else None


READERS: dict[str, Callable[[Any], Any]] = {
    "text": _text,
    "otext": _original_text,
    "lang": lambda n: n.get("language"),
    "id": lambda n: n.get("extension"),
    "ref": _ref,
    "ts": _ts,
    "coded": _coded,
    "coded_or_text": lambda n: _coded(n) if n.get("code") is not None else _text(n),
    "bool": _bool,
    "pq": _pq,
    "ed": lambda n: Attachment(
        media_type=n.get("mediaType"), representation=n.get("representation"), data=_text(n)
    ),
}

# Kinds that describe identifiers/attributes, where a nullFlavor is not meaningful.
_NO_NULLFLAVOR = {"lang", "ref"}


def _null(node: Any) -> Null:
    code = node.get("nullFlavor")
    try:
        return Null(null_flavor=NullFlavor(code))
    except ValueError as exc:
        raise E2BParseError(
            f"line {node.sourceline}: nullFlavor {code!r} is not allowed by the E2B(R3) IG"
        ) from exc


def read(ctx: Any, eid: str) -> Any:
    """Read data element ``eid`` from its context node: value, :class:`Null`, or None (absent)."""
    found = _XPATH[eid](ctx)
    if not found:
        return None
    node = found[0]
    kind = MAPPING[eid].kind
    if kind not in _NO_NULLFLAVOR and node.get("nullFlavor") is not None:
        return _null(node)
    return READERS[kind](node)


def group(ctx: Any, eid: str) -> list[Any]:
    """All context nodes of repeating group ``eid``."""
    return list(_XPATH[eid](ctx))


# --------------------------------------------------------------------------- regional (FR-8)


def _region(oid: Optional[str]) -> Optional[str]:
    if not oid:
        return None
    for arc, region in REGIONAL_ARCS.items():
        if oid == arc or oid.startswith(arc + "."):
            return region
    return None


def _render(node: Any) -> str:
    nf = node.get("nullFlavor")
    if nf is not None:
        return f"nullFlavor={nf}"
    for attr in ("code", "extension"):
        if node.get(attr) is not None:
            return node.get(attr)
    if node.get("value") is not None:
        unit = node.get("unit")
        return node.get("value") + (f" {unit}" if unit else "")
    return _text(node).strip()


def regional(ie: Any) -> dict[str, str]:
    """Collect FDA.* / EU regional elements under an investigationEvent as raw key-value pairs.

    An element is regional when its ``@codeSystem`` (or an ``id``'s ``@root``) is in
    a regional OID arc (see :data:`e2br3.mapping.REGIONAL_ARCS`). Keys:

    * ``REGION:<codeSystem>:<code>`` for an observation-style ``code`` with a sibling
      ``value``; the value is the rendered sibling.
    * ``REGION:<element>:<oid>`` for any other regional element (coded values, ids).

    Repeats get ``[2]``, ``[3]`` ... suffixes in document order.
    """
    out: dict[str, str] = {}
    seen: set[Any] = set()
    for el in ie.iter(etree.Element):
        if el in seen:
            continue
        local = etree.QName(el).localname
        oid = el.get("root") if local == "id" else el.get("codeSystem")
        region = _region(oid)
        if region is None:
            continue
        sibling = _VALUE(el.getparent()) if local == "code" else []
        if sibling:
            key, val = f"{region}:{oid}:{el.get('code')}", _render(sibling[0])
            seen.add(sibling[0])
        else:
            key, val = f"{region}:{local}:{oid}", _render(el)
        if key in out:
            n = 2
            while f"{key}[{n}]" in out:
                n += 1
            key = f"{key}[{n}]"
        out[key] = val
    return out


# --------------------------------------------------------------------------- builders


def _patient(node: Any) -> Patient:
    return Patient(name=read(node, "D.1"), age=read(node, "D.2.2"), sex=read(node, "D.5"))


def _reaction(node: Any) -> Reaction:
    return Reaction(
        id=read(node, "E.i.id"),
        native_term=read(node, "E.i.1.1a"),
        native_language=read(node, "E.i.1.1b"),
        translated_term=read(node, "E.i.1.2"),
        meddra=read(node, "E.i.2.1"),
        start_date=read(node, "E.i.4"),
        end_date=read(node, "E.i.5"),
        results_in_death=read(node, "E.i.3.2a"),
        life_threatening=read(node, "E.i.3.2b"),
        hospitalisation=read(node, "E.i.3.2c"),
        disabling=read(node, "E.i.3.2d"),
        congenital_anomaly=read(node, "E.i.3.2e"),
        other_medically_important=read(node, "E.i.3.2f"),
        outcome=read(node, "E.i.7"),
    )


def _dosage(node: Any) -> Dosage:
    return Dosage(
        text=read(node, "G.k.4.r.8"),
        route_text=read(node, "G.k.4.r.10.1"),
        route=read(node, "G.k.4.r.10.2"),
    )


def _drugs(ie: Any, patient: Any, reaction_index: dict[str, int]) -> list[Drug]:
    roles: dict[Optional[str], Any] = {}
    for node in group(ie, "G.k.1@"):
        roles.setdefault(read(node, "G.k.1.drug"), read(node, "G.k.1"))

    # drug id -> reaction id -> assessments, in document order
    matrix: dict[Optional[str], dict[Optional[str], list[Assessment]]] = defaultdict(dict)
    for node in group(ie, "G.k.9.i.2.r"):
        assessment = Assessment(
            source=read(node, "G.k.9.i.2.r.1"),
            method=read(node, "G.k.9.i.2.r.2"),
            result=read(node, "G.k.9.i.2.r.3"),
        )
        per_drug = matrix[read(node, "G.k.9.i.drug")]
        per_drug.setdefault(read(node, "G.k.9.i.1"), []).append(assessment)

    drugs = []
    for node in group(patient, "G.k") if patient is not None else []:
        drug_id = read(node, "G.k.id")
        drugs.append(
            Drug(
                id=drug_id,
                role=roles.get(drug_id) if drug_id is not None else None,
                product_name=read(node, "G.k.2.2"),
                substances=[read(s, "G.k.2.3.r.1") for s in group(node, "G.k.2.3.r")],
                dosages=[_dosage(d) for d in group(node, "G.k.4.r")],
                action_taken=read(node, "G.k.8"),
                relatedness=[
                    DrugReaction(
                        reaction_id=rid,
                        reaction_index=reaction_index.get(rid) if rid is not None else None,
                        assessments=items,
                    )
                    for rid, items in (matrix.get(drug_id, {}) if drug_id is not None else {}).items()
                ],
            )
        )
    return drugs


def _icsr(ie: Any) -> ICSR:
    patients = group(ie, "D")
    patient = patients[0] if patients else None
    reactions = [_reaction(r) for r in group(patient, "E.i")] if patient is not None else []
    reaction_index = {r.id: i for i, r in enumerate(reactions) if r.id is not None}
    return ICSR(
        safety_report_id=read(ie, "C.1.1"),
        creation_date=read(ie, "C.1.2"),
        report_type=read(ie, "C.1.3"),
        first_received_date=read(ie, "C.1.4"),
        most_recent_date=read(ie, "C.1.5"),
        worldwide_case_id=read(ie, "C.1.8.1"),
        nullification_amendment=read(ie, "C.1.11.1"),
        nullification_reason=read(ie, "C.1.11.2"),
        primary_sources=[
            PrimarySource(country=read(p, "C.2.r.3"), qualification=read(p, "C.2.r.4"))
            for p in group(ie, "C.2.r")
        ],
        literature=[
            Literature(reference=read(d, "C.4.r.1"), document=read(d, "C.4.r.2")) for d in group(ie, "C.4.r")
        ],
        patient=_patient(patient) if patient is not None else None,
        reactions=reactions,
        drugs=_drugs(ie, patient, reaction_index),
        narrative=read(ie, "H.1"),
        regional=regional(ie),
    )


def _message(node: Any) -> Message:
    events = group(node, "ICSR")
    return Message(
        message_id=read(node, "N.2.r.1"),
        sender=read(node, "N.2.r.2"),
        receiver=read(node, "N.2.r.3"),
        creation_date=read(node, "N.2.r.4"),
        icsr=_icsr(events[0]) if events else None,
    )


def parse(source: Source) -> Batch:
    """Parse an E2B(R3) ICSR batch (``MCCI_IN200100UV01``) from a path or bytes.

    Raises :class:`E2BParseError` if the input is not well-formed XML or is not
    an ICSR batch (for example an ACK, which is out of scope for v0.1).
    """
    root = load_tree(source).getroot()
    qname = etree.QName(root)
    if qname.namespace != HL7_NS or qname.localname != BATCH_ROOT:
        raise E2BParseError(
            f"expected an HL7 {BATCH_ROOT} ICSR batch, got {qname.localname!r}"
            + (" (acknowledgement messages are out of scope)" if qname.localname.startswith("MCCI_IN2001") else "")
        )
    return Batch(
        batch_type=read(root, "N.1.1"),
        batch_number=read(root, "N.1.2"),
        sender=read(root, "N.1.3"),
        receiver=read(root, "N.1.4"),
        transmission_date=read(root, "N.1.5"),
        messages=[_message(m) for m in group(root, "N.2.r")],
    )
