"""Data-element ID -> XPath mapping for the v0.1 core subset.

This table is the core artefact of the library. Each entry says where an ICH
E2B(R3) data element lives in the HL7 v3 message, relative to a *context node*,
and how to read it. Section numbers refer to the ICH E2B(R3) Implementation
Guide v5.03 (Jul 2025), whose data-element sections are numbered by the
element IDs themselves (C.1, C.2.r, ... H.1), and to the message structure
in its Appendix I. Observation code numbers come from ICH code
list 19 (``2.16.840.1.113883.3.989.2.1.1.19``, "observation codes") unless
noted otherwise.

Contexts (where each relative XPath starts):

==================  ==========================================================
``batch``           ``MCCI_IN200100UV01`` root (N.1)
``message``         ``PORR_IN049016UV`` (N.2.r)
``icsr``            ``controlActProcess/subject/investigationEvent`` (C, H)
``primary_source``  ``assignedEntity`` of a C.2.r ``relatedInvestigation``
``literature``      ``reference/document`` with code-list-27 code 2 (C.4.r)
``patient``         ``adverseEventAssessment/subject1/primaryRole`` (D)
``reaction``        an E.i ``observation`` (code 29)
``drug``            a G.k ``substanceAdministration``
``dosage``          a G.k.4.r nested ``substanceAdministration``
``role``            a ``causalityAssessment`` with code 20 (G.k.1)
``assessment``      a ``causalityAssessment`` with code 39 (G.k.9.i.2.r)
``substance``       a G.k.2.3.r ``ingredientSubstance``
==================  ==========================================================

Kinds (how the selected element is read; see :mod:`e2br3.parse`):

``text``   string value of the element (``ST``/``ED`` content)
``otext``  string value of its ``originalText`` child
``lang``   its ``@language`` attribute
``id``     its ``@extension`` attribute (an ``II``)
``ref``    ``@root`` (+ ``|@extension``) of an ``II`` used as an internal reference
``ts``     ``@value`` as an HL7 TS
``coded``  ``@code/@codeSystem/@codeSystemVersion/@displayName`` + ``originalText``
``coded_or_text``  ``coded`` if the element has ``@code``, else ``text``
``bool``   ``BL`` ``@value``
``pq``     ``PQ`` ``@value`` + ``@unit``
``ed``     ``ED`` attachment: ``@mediaType``, ``@representation`` and content
``group``  a repeating group: every match becomes one context node

A ``nullFlavor`` on the selected element always wins over the kind.
"""
from __future__ import annotations

from dataclasses import dataclass

NS = {"h": "urn:hl7-org:v3", "xsi": "http://www.w3.org/2001/XMLSchema-instance"}

# OIDs (IG section 3.2 and the ICH OID list)
OID_ICH_CODE_LIST = "2.16.840.1.113883.3.989.2.1.1"
OID_OBS = OID_ICH_CODE_LIST + ".19"  # code list 19: observation codes
OID_MEDDRA = "2.16.840.1.113883.6.163"
OID_C11_SENDER_ID = "2.16.840.1.113883.3.989.2.1.3.1"  # C.1.1 / N.2.r.1 id root
OID_C181_WORLDWIDE_ID = "2.16.840.1.113883.3.989.2.1.3.2"  # C.1.8.1 id root

#: Regional OID arcs (FR-8). ``...989.5.1.1`` is the EU arc and ``...989.5.1.2``
#: the FDA arc; FDA also uses NCI Thesaurus codes for its regional elements.
REGIONAL_ARCS = {
    "2.16.840.1.113883.3.989.5.1.1": "EU",
    "2.16.840.1.113883.3.989.5.1.2": "FDA",
    "2.16.840.1.113883.3.26.1.1": "FDA",
}


def _obs(code: str) -> str:
    """Predicate selecting an element whose ``code`` is ``code`` in code list 19."""
    return f"[h:code[@code='{code}'][@codeSystem='{OID_OBS}']]"


def _list(code: str, list_no: int) -> str:
    """Predicate selecting an element whose ``code`` is ``code`` in ICH code list ``list_no``."""
    return f"[h:code[@code='{code}'][@codeSystem='{OID_ICH_CODE_LIST}.{list_no}']]"


@dataclass(frozen=True)
class Element:
    context: str
    xpath: str
    kind: str


E = Element

# Shared sub-paths
_AEA = "h:component/h:adverseEventAssessment"
_PRODUCT = "h:consumable/h:instanceOfKind/h:kindOfProduct"
_REACTION_REL = "h:outboundRelationship2/h:observation"

MAPPING: dict[str, Element] = {
    # ---- IG section N.1: Batch wrapper; Appendix I(A) MCCI_IN200100UV01 ----------------------
    "N.1.1": E("batch", "h:name", "coded"),
    "N.1.2": E("batch", "h:id", "id"),
    "N.1.3": E("batch", "h:sender/h:device/h:id", "id"),
    "N.1.4": E("batch", "h:receiver/h:device/h:id", "id"),
    "N.1.5": E("batch", "h:creationTime", "ts"),
    "N.2.r": E("batch", "h:PORR_IN049016UV", "group"),
    # ---- IG section N.2.r: Message wrapper ---------------------------------------------------
    "N.2.r.1": E("message", "h:id", "id"),
    "N.2.r.2": E("message", "h:sender/h:device/h:id", "id"),
    "N.2.r.3": E("message", "h:receiver/h:device/h:id", "id"),
    "N.2.r.4": E("message", "h:creationTime", "ts"),
    "ICSR": E("message", "h:controlActProcess/h:subject/h:investigationEvent", "group"),
    # ---- IG section C.1: Identification of the case safety report ----------------------------
    "C.1.1": E("icsr", f"h:id[@root='{OID_C11_SENDER_ID}']", "id"),
    # C.1.2 sits on controlActProcess, two levels above investigationEvent.
    "C.1.2": E("icsr", "../../h:effectiveTime", "ts"),
    # C.1.3: investigationCharacteristic code 1 in code list 23.
    "C.1.3": E("icsr", "h:subjectOf2/h:investigationCharacteristic" + _list("1", 23) + "/h:value", "coded"),
    "C.1.4": E("icsr", "h:effectiveTime/h:low", "ts"),
    "C.1.5": E("icsr", "h:availabilityTime", "ts"),
    "C.1.8.1": E("icsr", f"h:id[@root='{OID_C181_WORLDWIDE_ID}']", "id"),
    # C.1.11.1/2: investigationCharacteristic codes 3 and 4 in code list 23.
    "C.1.11.1": E("icsr", "h:subjectOf2/h:investigationCharacteristic" + _list("3", 23) + "/h:value", "coded"),
    "C.1.11.2": E("icsr", "h:subjectOf2/h:investigationCharacteristic" + _list("4", 23) + "/h:value", "otext"),
    # ---- IG section C.2.r: Primary source(s); relatedInvestigation code 2 in list 22 ---------
    "C.2.r": E(
        "icsr",
        "h:outboundRelationship[@typeCode='SPRT']/h:relatedInvestigation" + _list("2", 22)
        + "/h:subjectOf2/h:controlActEvent/h:author/h:assignedEntity",
        "group",
    ),
    "C.2.r.3": E("primary_source", "h:assignedPerson/h:asLocatedEntity/h:location/h:code", "coded"),
    "C.2.r.4": E("primary_source", "h:assignedPerson/h:asQualifiedEntity/h:code", "coded"),
    # ---- IG section C.4.r: Literature reference(s); document code 2 in list 27 ---------------
    "C.4.r": E("icsr", "h:reference[@typeCode='REFR']/h:document" + _list("2", 27), "group"),
    "C.4.r.1": E("literature", "h:bibliographicDesignationText", "text"),
    "C.4.r.2": E("literature", "h:text", "ed"),
    # ---- IG section D: Patient characteristics -----------------------------------------------
    "D": E("icsr", f"{_AEA}/h:subject1/h:primaryRole", "group"),
    "D.1": E("patient", "h:player1/h:name", "text"),
    "D.2.2": E("patient", "h:subjectOf2/h:observation" + _obs("3") + "/h:value", "pq"),
    "D.5": E("patient", "h:player1/h:administrativeGenderCode", "coded"),
    # ---- IG section E.i: Reaction(s) / event(s); observation code 29 -------------------------
    "E.i": E("patient", "h:subjectOf2/h:observation" + _obs("29"), "group"),
    "E.i.id": E("reaction", "h:id", "ref"),
    "E.i.1.1a": E("reaction", "h:value/h:originalText", "text"),
    "E.i.1.1b": E("reaction", "h:value/h:originalText", "lang"),
    "E.i.1.2": E("reaction", _REACTION_REL + _obs("30") + "/h:value", "text"),
    "E.i.2.1": E("reaction", "h:value", "coded"),  # a: codeSystemVersion, b: code (MedDRA LLT)
    # effectiveTime is IVL_TS, or SXPR_TS whose first comp carries low/high (E.i.6 is the width comp).
    "E.i.4": E("reaction", "h:effectiveTime/h:low | h:effectiveTime/h:comp/h:low", "ts"),
    "E.i.5": E("reaction", "h:effectiveTime/h:high | h:effectiveTime/h:comp/h:high", "ts"),
    "E.i.3.2a": E("reaction", _REACTION_REL + _obs("34") + "/h:value", "bool"),
    "E.i.3.2b": E("reaction", _REACTION_REL + _obs("21") + "/h:value", "bool"),
    "E.i.3.2c": E("reaction", _REACTION_REL + _obs("33") + "/h:value", "bool"),
    "E.i.3.2d": E("reaction", _REACTION_REL + _obs("35") + "/h:value", "bool"),
    "E.i.3.2e": E("reaction", _REACTION_REL + _obs("12") + "/h:value", "bool"),
    "E.i.3.2f": E("reaction", _REACTION_REL + _obs("26") + "/h:value", "bool"),
    "E.i.7": E("reaction", _REACTION_REL + _obs("27") + "/h:value", "coded"),
    # ---- IG section G.k: Drug(s) information; organizer code 4 in list 20 --------------------
    "G.k": E("patient", "h:subjectOf2/h:organizer" + _list("4", 20) + "/h:component/h:substanceAdministration", "group"),
    "G.k.id": E("drug", "h:id", "ref"),
    # G.k.1 is a causalityAssessment (code 20) under adverseEventAssessment that points
    # at the drug through subject2/productUseReference/id.
    "G.k.1@": E("icsr", f"{_AEA}/h:component/h:causalityAssessment" + _obs("20"), "group"),
    "G.k.1": E("role", "h:value", "coded"),
    "G.k.1.drug": E("role", "h:subject2/h:productUseReference/h:id", "ref"),
    "G.k.2.2": E("drug", f"{_PRODUCT}/h:name", "text"),
    "G.k.2.3.r": E("drug", f"{_PRODUCT}/h:ingredient/h:ingredientSubstance", "group"),
    "G.k.2.3.r.1": E("substance", "h:name", "text"),
    "G.k.4.r": E("drug", "h:outboundRelationship2[@typeCode='COMP']/h:substanceAdministration", "group"),
    "G.k.4.r.8": E("dosage", "h:text", "text"),
    "G.k.4.r.10.1": E("dosage", "h:routeCode/h:originalText", "text"),
    "G.k.4.r.10.2": E("dosage", "h:routeCode", "coded"),  # a: codeSystemVersion, b: code
    "G.k.8": E("drug", "h:inboundRelationship[@typeCode='CAUS']/h:act/h:code", "coded"),
    # G.k.9.i.2.r: causalityAssessment code 39, linking a reaction (subject1) and a drug (subject2).
    "G.k.9.i.2.r": E("icsr", f"{_AEA}/h:component/h:causalityAssessment" + _obs("39"), "group"),
    "G.k.9.i.1": E("assessment", "h:subject1/h:adverseEffectReference/h:id", "ref"),
    "G.k.9.i.drug": E("assessment", "h:subject2/h:productUseReference/h:id", "ref"),
    "G.k.9.i.2.r.1": E("assessment", "h:author/h:assignedEntity/h:code", "coded"),
    "G.k.9.i.2.r.2": E("assessment", "h:methodCode", "coded"),
    "G.k.9.i.2.r.3": E("assessment", "h:value", "coded_or_text"),
    # ---- IG section H: Narrative -------------------------------------------------------------
    "H.1": E("icsr", "h:text", "text"),
}
