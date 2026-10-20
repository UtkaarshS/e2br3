"""``validate()``: XSD validation against the local ICH ICSR Schema Set v2.5 (SRS FR-5).

The schema is always loaded from local files and never fetched: the parser
used for both the instance and the XSDs has ``no_network=True``. The EMA
samples point ``xsi:schemaLocation`` at a remote URL that returns HTML, so
``schemaLocation`` is ignored entirely.

Schema lookup order:

1. the ``schema_dir`` argument,
2. the ``E2BR3_SCHEMA_DIR`` environment variable,
3. ``schemas/ich-v2.5`` in a source checkout (fetched by ``scripts/fetch_fixtures.py``).

The directory is the root of the ICH set (it contains ``multicacheschemas/``).
The XSD for the document's root element (``MCCI_IN200100UV01`` for a batch,
``MCCI_IN200101UV01`` for an ACK) is chosen automatically.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Optional, Union

from lxml import etree
from pydantic import BaseModel

from .parse import Source, has_dtd, make_parser

ENV_VAR = "E2BR3_SCHEMA_DIR"
_CHECKOUT_SCHEMAS = Path(__file__).resolve().parents[2] / "schemas" / "ich-v2.5"


class ValidationError(BaseModel):
    """One problem found while validating an instance."""

    line: Optional[int] = None
    column: Optional[int] = None
    message: str
    kind: str = "schema"  # "schema" (XSD), "syntax" (not well-formed) or "security" (DTD refused)

    def __str__(self) -> str:
        return f"{self.line}:{self.column}: {self.message}"


class SchemaNotFoundError(FileNotFoundError):
    """The local ICH XSD set could not be located."""


def find_schema_dir(schema_dir: Union[str, "os.PathLike[str]", None] = None) -> Path:
    """Locate the ICH XSD set. An explicit ``schema_dir`` is used alone, without fallbacks."""
    candidates = [schema_dir] if schema_dir is not None else [os.environ.get(ENV_VAR), _CHECKOUT_SCHEMAS]
    for cand in candidates:
        if cand and (Path(cand) / "multicacheschemas").is_dir():
            return Path(cand).resolve()
    raise SchemaNotFoundError(
        "ICH ICSR XSD set v2.5 not found. Pass schema_dir=, set "
        f"{ENV_VAR}, or run scripts/fetch_fixtures.py in a source checkout."
    )


@lru_cache(maxsize=8)
def load_schema(xsd_path: str) -> etree.XMLSchema:
    """Load (and cache) one XSD from disk, with network access disabled."""
    doc = etree.parse(xsd_path, make_parser())
    return etree.XMLSchema(doc)


def validate(source: Source, schema_dir: Union[str, "os.PathLike[str]", None] = None) -> list[ValidationError]:
    """Validate an instance against the local ICH XSD. Returns [] when valid.

    Not well-formed input yields a single ``kind="syntax"`` error rather than an
    exception. A missing schema set raises :class:`SchemaNotFoundError`.
    """
    parser = make_parser()
    try:
        if isinstance(source, (bytes, bytearray)):
            doc = etree.ElementTree(etree.fromstring(bytes(source), parser))
        else:
            doc = etree.parse(str(Path(source)), parser)
    except etree.XMLSyntaxError as exc:
        line, col = (exc.position if exc.position else (None, None))
        return [ValidationError(line=line, column=col, message=str(exc), kind="syntax")]

    if has_dtd(doc):
        return [ValidationError(line=1, message="DOCTYPE/DTD not allowed in E2B(R3) XML; refused", kind="security")]

    root_name = etree.QName(doc.getroot()).localname
    xsd = find_schema_dir(schema_dir) / "multicacheschemas" / f"{root_name}.xsd"
    if not xsd.is_file():
        return [ValidationError(line=doc.getroot().sourceline, message=f"no ICH schema for root element {root_name!r}")]

    schema = load_schema(str(xsd))
    if schema.validate(doc):
        return []
    return [ValidationError(line=e.line, column=e.column, message=e.message) for e in schema.error_log]
