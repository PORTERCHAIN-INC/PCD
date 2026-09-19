"""Shared result type for independently priced delivery components."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from porterchain_pricing.types import PriceLineItem


@dataclass(frozen=True)
class ComponentQuote:
    """
    What one pricing component charges, on its own.

    Every component returns this shape so callers can price elements
    independently and compose only the ones a given route needs.
    """

    component: str
    items: list[PriceLineItem] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def total_cents(self) -> int:
        return sum(i.amount_cents for i in self.items)

    @property
    def applies(self) -> bool:
        """False when the component had nothing to charge for this delivery."""
        return bool(self.items)

    def to_dict(self) -> dict[str, Any]:
        return {
            "component": self.component,
            "total_cents": self.total_cents,
            "items": [
                {"code": i.code, "label": i.label, "amount_cents": i.amount_cents} for i in self.items
            ],
            "metadata": self.metadata,
        }


def _item(code: str, label: str, amount_cents: int) -> list[PriceLineItem]:
    """One line item, or none when the amount rounds to zero."""
    if not amount_cents:
        return []
    return [PriceLineItem(code=code, label=label, amount_cents=amount_cents)]
