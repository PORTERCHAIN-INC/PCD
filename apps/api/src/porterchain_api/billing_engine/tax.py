"""Invoice tax: destination-province GST/HST/QST, exclusive or inclusive prices.

Rule (finance setting ``tax_mode``):

* ``exclusive`` (default, the B2B norm): the delivery price is before tax and tax is added
  on top. If the quote already added tax (``compliance_metadata.quote.tax_cents``) we
  take it back out first, so the invoice shows one clean pre-tax amount + the correct
  tax for the *destination* province (CRA place of supply for freight).
* ``inclusive``: the charged amount already includes tax; tax is extracted
  ``gross × r / (1 + r)``.

Invoice rows keep one invariant everywhere: ``invoice.amount_cents`` is the gross
(tax-included) total and ``invoice.tax_cents`` is the tax part of it. So the merchant tax
summary (subtotal = amount − tax) and the HST report read the same numbers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from porterchain_pricing.tax.provinces import PROVINCES, province_from_address


@dataclass(frozen=True)
class TaxSplit:
    pretax_cents: int
    tax_cents: int
    gross_cents: int
    province: str
    percent: float
    label: str


def _settings(db: Session) -> tuple[str, str, bool]:
    from porterchain_api.platform.merchant_billing import finance_tax_settings

    return finance_tax_settings(db)


def order_province(order: Any, default: str = "ON") -> str:
    dropoff = getattr(order, "dropoff", None)
    got = province_from_address(dropoff if isinstance(dropoff, dict) else None)
    if not got:
        meta = getattr(order, "compliance_metadata", None)
        stops = (meta or {}).get("stops") if isinstance(meta, dict) else None
        if isinstance(stops, list) and stops:
            last = stops[-1] if isinstance(stops[-1], dict) else {}
            got = province_from_address(last.get("address") if isinstance(last.get("address"), dict) else last)
    return got or default


def quoted_tax_cents(order: Any) -> int | None:
    meta = getattr(order, "compliance_metadata", None)
    quote = meta.get("quote") if isinstance(meta, dict) else None
    raw = quote.get("tax_cents") if isinstance(quote, dict) else None
    try:
        return int(raw) if raw is not None else None
    except (TypeError, ValueError):
        return None


def split_amount(amount_cents: int, *, province: str, mode: str, collect_qst: bool, quoted_tax: int | None = None) -> TaxSplit:
    prov = PROVINCES.get(province) or PROVINCES["ON"]
    pct = prov.freight_percent(collect_qst=collect_qst)
    label = prov.label(collect_qst=collect_qst)
    amount = max(0, int(amount_cents or 0))
    if mode == "inclusive":
        tax = int(round(amount * pct / (100.0 + pct)))
        return TaxSplit(amount - tax, tax, amount, prov.province, pct, label)
    pretax = max(0, amount - int(quoted_tax or 0))
    tax = int(round(pretax * pct / 100.0))
    return TaxSplit(pretax, tax, pretax + tax, prov.province, pct, label)


def order_tax_split(db: Session, order: Any) -> TaxSplit:
    """Pre-tax / tax / gross for one merchant delivery on a cycle (Interac) invoice."""
    mode, default_prov, qst = _settings(db)
    return split_amount(
        int(order.amount_cents or 0),
        province=order_province(order, default_prov),
        mode=mode,
        collect_qst=qst,
        quoted_tax=quoted_tax_cents(order),
    )


def charged_tax_split(db: Session, order: Any, charged_cents: int) -> TaxSplit:
    """Tax inside an amount already charged (Stripe): never changes what was paid."""
    _mode, default_prov, qst = _settings(db)
    prov = order_province(order, default_prov) if order is not None else default_prov
    return split_amount(charged_cents, province=prov, mode="inclusive", collect_qst=qst)
