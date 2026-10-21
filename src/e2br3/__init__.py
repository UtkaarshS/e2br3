"""e2br3: read-only parser and validator for ICH E2B(R3) ICSR XML.

>>> import e2br3
>>> batch = e2br3.parse("case.xml")          # Batch -> messages -> icsr
>>> errors = e2br3.validate("case.xml")      # [] when the XSD accepts it
>>> data = batch.to_dict()                   # JSON-safe; nullFlavor -> {"nullFlavor": "UNK"}
>>> tables = batch.to_rows("case.xml")       # cases, reactions, drugs, drug_reaction
"""
from .models import (
    ICSR,
    TS,
    Assessment,
    Attachment,
    Batch,
    Coded,
    Dosage,
    Drug,
    DrugReaction,
    Literature,
    Message,
    Patient,
    PrimarySource,
    Quantity,
    Reaction,
)
from .export import to_dict, to_frames, to_json, to_rows
from .nullflavor import Null, NullFlavor, Nullable, flavor_of, is_null
from .parse import E2BParseError, parse
from .validate import SchemaNotFoundError, ValidationError, validate

__version__ = "0.1.1"

__all__ = [
    "parse",
    "validate",
    "to_dict",
    "to_json",
    "to_rows",
    "to_frames",
    "E2BParseError",
    "SchemaNotFoundError",
    "ValidationError",
    "Null",
    "NullFlavor",
    "Nullable",
    "is_null",
    "flavor_of",
    "Batch",
    "Message",
    "ICSR",
    "PrimarySource",
    "Literature",
    "Patient",
    "Reaction",
    "Drug",
    "Dosage",
    "DrugReaction",
    "Assessment",
    "Coded",
    "TS",
    "Quantity",
    "Attachment",
]
