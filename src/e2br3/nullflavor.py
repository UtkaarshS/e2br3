"""HL7 nullFlavor handling (ICH E2B(R3) IG section 3.3.6).

Every parsed field has three distinct states:

* a value (``str``, ``bool``, ``Coded``, ``TS`` ...),
* a :class:`Null` carrying the :class:`NullFlavor` the sender supplied, or
* ``None``, meaning the element was truly absent from the XML.

A nullFlavor is never collapsed to ``None``. It is wrapped in :class:`Null`
rather than stored as a bare enum so that a legitimate string value such as
``"NA"`` (initials, a lot number) can never be confused with ``nullFlavor="NA"``,
including after a JSON round trip.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, TypeVar, Union

from pydantic import BaseModel, ConfigDict


class NullFlavor(str, Enum):
    """The nullFlavor codes allowed by the E2B(R3) IG (section 3.3.6)."""

    NI = "NI"  # No information
    MSK = "MSK"  # Masked (privacy / confidentiality)
    UNK = "UNK"  # Unknown
    NA = "NA"  # Not applicable
    ASKU = "ASKU"  # Asked but unknown
    NASK = "NASK"  # Not asked
    NINF = "NINF"  # Negative infinity (F.r.3.2 ranges only)
    PINF = "PINF"  # Positive infinity (F.r.3.2 ranges only)


class Null(BaseModel):
    """An element that is present but carries a nullFlavor instead of a value."""

    model_config = ConfigDict(frozen=True)

    null_flavor: NullFlavor

    def __bool__(self) -> bool:  # a Null is never truthy
        return False

    def __str__(self) -> str:
        return f"nullFlavor={self.null_flavor.value}"


T = TypeVar("T")

#: ``Value | Null | None`` where ``None`` means "element absent".
Nullable = Union[T, Null, None]


def is_null(value: Any) -> bool:
    """True when ``value`` is a :class:`Null` (a nullFlavor was supplied)."""
    return isinstance(value, Null)


def flavor_of(value: Any) -> NullFlavor | None:
    """Return the NullFlavor of ``value`` or ``None`` if it is not a :class:`Null`."""
    return value.null_flavor if isinstance(value, Null) else None


def make_null(code: str) -> Null:
    """Build a :class:`Null` from a nullFlavor attribute value.

    Unknown codes raise ``ValueError``; the XSD restricts nullFlavor to the HL7
    vocabulary, and the IG restricts it further to the eight codes above.
    """
    return Null(null_flavor=NullFlavor(code))
