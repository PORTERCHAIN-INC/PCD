"""Stop/Route model — every pickup/delivery shape as pickup→delivery pairs.

Shapes: 1→1, 1→N (one pickup, many drops), N→1 (consolidation), N→N, and returns
(the customer address becomes a ``return_pickup``; the merchant/warehouse a ``return_drop``).
Partner legs add ``hub`` (warehouse cross-dock) and ``handoff`` (FTL/LTL/3PL) drops.

Multi-stop orders carry ``stops: [...]`` inside ``order.pickup`` / ``order.dropoff``.
Pure: no DB, no network. Each pair becomes one solver task; a pickup shared by
several drops is split into one node per pair (zero distance between copies).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

KINDS = ("pickup", "drop", "return_pickup", "return_drop", "hub", "handoff")
PICKUP_KINDS = {"pickup", "return_pickup"}


@dataclass
class StopSpec:
    key: str
    order_id: str
    kind: str
    lat: float
    lng: float
    fsa: str | None = None
    label: str = ""
    boxes: int = 0
    kg: float = 0.0
    m3: float = 0.0
    service_s: int = 300
    window_start_s: int | None = None
    window_end_s: int | None = None
    partner_id: str | None = None
    rush: bool = False  # same-day rush (EXPRESS): last to be dropped when the fleet is full

    def public(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class OrderStops:
    order_id: str
    shape: str
    stops: list[StopSpec] = field(default_factory=list)
    pairs: list[tuple[str, str]] = field(default_factory=list)
    skipped: str | None = None


def fsa(postal: Any) -> str | None:
    """Canadian forward sortation area (first 3 chars of the postal code)."""
    s = "".join(ch for ch in str(postal or "") if ch.isalnum()).upper()
    return s[:3] if len(s) >= 3 and s[0].isalpha() and s[1].isdigit() else None


def _points(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, dict):
        return []
    inner = raw.get("stops")
    if isinstance(inner, list) and inner:
        return [p for p in inner if isinstance(p, dict)]
    return [raw]


def _coord(p: dict[str, Any]) -> tuple[float, float] | None:
    lat, lng = p.get("lat"), p.get("lng")
    if lat is None or lng is None:
        return None
    try:
        return float(lat), float(lng)
    except (TypeError, ValueError):
        return None


def _postal(p: dict[str, Any]) -> Any:
    return p.get("postal") or p.get("postal_code") or p.get("zip")


def is_return(order: Any) -> bool:
    meta = getattr(order, "compliance_metadata", None) or {}
    otype = str(getattr(order, "order_type", "") or "").lower()
    state = str(getattr(order, "state", "") or "").upper()
    return bool(meta.get("is_return")) or otype == "return" or state.startswith("RETURN")


def shape_label(n_pickups: int, n_drops: int, *, returning: bool) -> str:
    a = "1" if n_pickups == 1 else "N"
    b = "1" if n_drops == 1 else "N"
    return f"return {a}→{b}" if returning else f"{a}→{b}"


def order_stops(order: Any, *, boxes: int = 0, kg: float = 0.0, m3: float = 0.0) -> OrderStops:
    """Expand one order into stops + pickup→drop pairs (load split evenly over pairs).

    Windows and learned service times are applied by the caller (``fleet_plan_service``).
    """
    oid = str(order.id)
    pickups = _points(getattr(order, "pickup", None))
    drops = _points(getattr(order, "dropoff", None))
    returning = is_return(order)
    rush = str(getattr(order, "order_type", "") or "").upper() == "EXPRESS"
    out = OrderStops(order_id=oid, shape=shape_label(len(pickups) or 1, len(drops) or 1, returning=returning))
    if not pickups or not drops:
        out.skipped = "missing pickup or drop"
        return out
    if any(_coord(p) is None for p in pickups + drops):
        out.skipped = "address not geocoded"
        return out

    # Pairing: 1→N and N→1 fan out; N→N zips unless a drop names its pickup_ref.
    pair_idx: list[tuple[int, int]] = []
    if len(pickups) == 1:
        pair_idx = [(0, j) for j in range(len(drops))]
    elif len(drops) == 1:
        pair_idx = [(i, 0) for i in range(len(pickups))]
    else:
        for j, d in enumerate(drops):
            ref = d.get("pickup_ref")
            i = int(ref) if isinstance(ref, int) and 0 <= ref < len(pickups) else min(j, len(pickups) - 1)
            pair_idx.append((i, j))

    n = len(pair_idx)
    b_each, b_rem = divmod(max(int(boxes), 0), n)
    kg_each = round(float(kg or 0) / n, 3)
    m3_each = round(float(m3 or 0) / n, 4)
    pk, dk = ("return_pickup", "return_drop") if returning else ("pickup", "drop")
    for k, (i, j) in enumerate(pair_idx):
        p, d = pickups[i], drops[j]
        pl, dl = _coord(p), _coord(d)
        assert pl and dl
        b = b_each + (1 if k < b_rem else 0)
        ps = StopSpec(
            key=f"{oid}:p{i}:{k}", order_id=oid, kind=pk, lat=pl[0], lng=pl[1], fsa=fsa(_postal(p)),
            label=str(p.get("formatted") or ""), boxes=b, kg=kg_each, m3=m3_each,
            service_s=int(p.get("service_s") or 300), rush=rush,
        )
        ds = StopSpec(
            key=f"{oid}:d{j}:{k}", order_id=oid, kind=str(d.get("kind") or dk) if d.get("kind") in KINDS else dk,
            lat=dl[0], lng=dl[1], fsa=fsa(_postal(d)), label=str(d.get("formatted") or ""), boxes=b, kg=kg_each, m3=m3_each,
            service_s=int(d.get("service_s") or 300), partner_id=d.get("partner_id"), rush=rush,
        )
        out.stops += [ps, ds]
        out.pairs.append((ps.key, ds.key))
    return out
