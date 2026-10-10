"""Canadian sales tax by province for a delivery (freight transportation) service.

CRA place of supply (ETA Sch. IX Part VI s.5): a freight transportation service is made
in the province of its *destination*. HST provinces charge the harmonized rate; the rest
charge 5% GST. PST (BC, SK, MB) does not apply to freight delivery services, so it is
listed for reporting with ``applies_to_freight=False``. Quebec QST applies only when the
business is QST-registered (finance setting ``collect_qst``).

Rates are percentages; confirm with an accountant when a rate changes (e.g. Nova Scotia
went from 15% to 14% HST on 2025-04-01).
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class TaxComponent:
    code: str  # HST | GST | PST | QST
    percent: float
    applies_to_freight: bool = True


@dataclass(frozen=True)
class ProvinceTax:
    province: str
    name: str
    components: tuple[TaxComponent, ...]

    def freight_components(self, *, collect_qst: bool = False) -> tuple[TaxComponent, ...]:
        out = []
        for c in self.components:
            if not c.applies_to_freight:
                continue
            if c.code == "QST" and not collect_qst:
                continue
            out.append(c)
        return tuple(out)

    def freight_percent(self, *, collect_qst: bool = False) -> float:
        return round(sum(c.percent for c in self.freight_components(collect_qst=collect_qst)), 4)

    def label(self, *, collect_qst: bool = False) -> str:
        return " + ".join(f"{c.code} {c.percent:g}%" for c in self.freight_components(collect_qst=collect_qst))


_GST = TaxComponent("GST", 5.0)
PROVINCES: dict[str, ProvinceTax] = {
    "ON": ProvinceTax("ON", "Ontario", (TaxComponent("HST", 13.0),)),
    "NB": ProvinceTax("NB", "New Brunswick", (TaxComponent("HST", 15.0),)),
    "NL": ProvinceTax("NL", "Newfoundland and Labrador", (TaxComponent("HST", 15.0),)),
    "NS": ProvinceTax("NS", "Nova Scotia", (TaxComponent("HST", 14.0),)),
    "PE": ProvinceTax("PE", "Prince Edward Island", (TaxComponent("HST", 15.0),)),
    "QC": ProvinceTax("QC", "Quebec", (_GST, TaxComponent("QST", 9.975))),
    "BC": ProvinceTax("BC", "British Columbia", (_GST, TaxComponent("PST", 7.0, applies_to_freight=False))),
    "SK": ProvinceTax("SK", "Saskatchewan", (_GST, TaxComponent("PST", 6.0, applies_to_freight=False))),
    "MB": ProvinceTax("MB", "Manitoba", (_GST, TaxComponent("PST", 7.0, applies_to_freight=False))),
    "AB": ProvinceTax("AB", "Alberta", (_GST,)),
    "YT": ProvinceTax("YT", "Yukon", (_GST,)),
    "NT": ProvinceTax("NT", "Northwest Territories", (_GST,)),
    "NU": ProvinceTax("NU", "Nunavut", (_GST,)),
}

# First letter of a Canadian postal code -> province (X is shared by NT/NU: report as NT).
_POSTAL = {
    "A": "NL", "B": "NS", "C": "PE", "E": "NB", "G": "QC", "H": "QC", "J": "QC",
    "K": "ON", "L": "ON", "M": "ON", "N": "ON", "P": "ON", "R": "MB", "S": "SK",
    "T": "AB", "V": "BC", "X": "NT", "Y": "YT",
}
_NAMES = {p.name.lower(): code for code, p in PROVINCES.items()} | {"québec": "QC", "pei": "PE"}
_POSTAL_RE = re.compile(r"\b([ABCEGHJ-NPRSTVXY])\d[ABCEGHJ-NPRSTV-Z]\s?\d[ABCEGHJ-NPRSTV-Z]\d\b", re.I)
_CODE_RE = re.compile(r"(?:,|\s)\s*(ON|QC|BC|AB|MB|SK|NS|NB|NL|PE|YT|NT|NU)\b(?:\s|,|$)")


def province_from_postal(postal: str | None) -> str | None:
    m = _POSTAL_RE.search(postal or "")
    return _POSTAL.get(m.group(1).upper()) if m else None


def province_from_address(address: dict | str | None) -> str | None:
    """Province code from a stored address dict (province/region/state, postal, formatted)."""
    if isinstance(address, dict):
        for key in ("province", "province_code", "region", "state", "administrative_area", "admin_area"):
            raw = str(address.get(key) or "").strip()
            if raw.upper() in PROVINCES:
                return raw.upper()
            if raw.lower() in _NAMES:
                return _NAMES[raw.lower()]
        for key in ("postal", "postal_code", "postcode", "zip"):
            got = province_from_postal(str(address.get(key) or ""))
            if got:
                return got
        text = str(address.get("formatted") or address.get("address") or address.get("line1") or "")
    else:
        text = str(address or "")
    got = province_from_postal(text)
    if got:
        return got
    m = _CODE_RE.search(" " + text.upper() + " ")
    return m.group(1) if m else None
