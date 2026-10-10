"""CRM shared helpers — time, actor, postal province, parsing."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any, Protocol


class CrmActorUser(Protocol):
    id: str


class CrmActor(Protocol):
    user: CrmActorUser


def _now() -> datetime:
    return datetime.now(UTC)


def _today() -> date:
    return _now().date()


def _actor(ctx: CrmActor | None) -> str | None:
    return ctx.user.id if ctx and ctx.user else None


# Canadian postal FSA first letter → province/territory code.
_POSTAL_PROVINCE = {
    "A": "NL",
    "B": "NS",
    "C": "PE",
    "E": "NB",
    "G": "QC",
    "H": "QC",
    "J": "QC",
    "K": "ON",
    "L": "ON",
    "M": "ON",
    "N": "ON",
    "P": "ON",
    "R": "MB",
    "S": "SK",
    "T": "AB",
    "V": "BC",
    "X": "NT",
    "Y": "YT",
}


def province_from_postal(postal: str | None) -> str | None:
    if not postal:
        return None
    first = postal.strip()[:1].upper()
    return _POSTAL_PROVINCE.get(first)


def _to_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(float(str(value).replace(",", "").replace("$", "")))
    except (ValueError, TypeError):
        return None


__all__ = [
    "CrmActor",
    "CrmActorUser",
    "province_from_postal",
    "_now",
    "_today",
    "_actor",
    "_to_int",
    "_POSTAL_PROVINCE",
]
