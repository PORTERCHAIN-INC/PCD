"""
Route pricing from a checked-in contract schedule (see `contract_schedule`).

Van: route pickup once, then every stop at its own destination tier. One
parcel is one stop, except standard parcels at or under the grouping size,
which share a stop up to the grouping count at the same destination. Each
handling-tier parcel adds its surcharge. The bill is the larger of that true
bill and the minimum of the highest tier on the route.

Compact: only when every destination is in the compact territory and every
parcel fits the packed limit; otherwise the whole load is priced as van. Stops
are counted per destination in groups of `parcels_per_stop`, the band picks the
stop rate and pickup, and the compact minimum replaces the van minimums.

Any destination the schedule does not price (unlisted, rural, custom-quote
list) and any parcel beyond the last handling tier refuses the whole route —
whatever order the stops arrive in.
"""

from __future__ import annotations

import math
from typing import Any

from porterchain_pricing.components.fsa import fsa_from_point
from porterchain_pricing.components.quote import ComponentQuote
from porterchain_pricing.components.size_weight import parse_dimensions_cm
from porterchain_pricing.contract_schedule import ContractSchedule, fits, footprint_cm
from porterchain_pricing.types import PriceLineItem, PricingRequest

COMPONENT = "contract_route"

Parcel = tuple[float | None, tuple[float | None, float | None, float | None]]


def parcels_by_stop(request: PricingRequest) -> list[list[Parcel]]:
    """
    Parcels at each stop (index 0 = dropoff).

    Without explicit `parcels`, each additional stop carries one parcel and the
    dropoff carries the rest of `parcel_count`; weight is split evenly and the
    request dimensions apply to every parcel.
    """
    n_stops = 1 + len(request.additional_stops or [])
    buckets: list[list[Parcel]] = [[] for _ in range(n_stops)]
    if request.parcels:
        for spec in request.parcels:
            idx = spec.stop_index if 0 <= spec.stop_index < n_stops else 0
            buckets[idx].append((spec.weight_kg, parse_dimensions_cm(spec.dimensions)))
    else:
        total = max(int(request.parcel_count or 1), n_stops)
        each_kg = (float(request.weight_kg) / total) if request.weight_kg else None
        dims = parse_dimensions_cm(request.dimensions)
        buckets[0] = [(each_kg, dims)] * (total - (n_stops - 1))
        for idx in range(1, n_stops):
            buckets[idx] = [(each_kg, dims)]
    for bucket in buckets:
        if not bucket:
            bucket.append((None, (None, None, None)))
    return buckets


def keys_by_stop(request: PricingRequest, buckets: list[list[Parcel]]) -> list[list[str | None]]:
    """`item_key` per parcel, aligned with `parcels_by_stop` (None = a parcel on its own)."""
    keys: list[list[str | None]] = [[None] * len(b) for b in buckets]
    if request.parcels:
        n_stops = len(buckets)
        seen = [0] * n_stops
        for spec in request.parcels:
            idx = spec.stop_index if 0 <= spec.stop_index < n_stops else 0
            if seen[idx] < len(keys[idx]):
                keys[idx][seen[idx]] = spec.item_key or None
            seen[idx] += 1
    return keys


def parcel_groups(bucket: list[Parcel], keys: list[str | None]) -> list[list[Parcel]]:
    """
    Parcels at one address: boxes sharing an `item_key` are ONE parcel (one item
    in several boxes); a box without a key is a parcel on its own.
    """
    groups: dict[str, list[Parcel]] = {}
    out: list[list[Parcel]] = []
    for i, box in enumerate(bucket):
        key = keys[i] if i < len(keys) else None
        if key:
            if key not in groups:
                groups[key] = []
                out.append(groups[key])
            groups[key].append(box)
        else:
            out.append([box])
    return out or [[(None, (None, None, None))]]


def _address_key(point: Any) -> str:
    """Same delivery address → same key (case, spacing and punctuation ignored)."""
    text = " ".join(str(getattr(point, "formatted", "") or "").upper().replace(",", " ").replace(".", " ").split())
    postal = "".join(str(getattr(point, "postal", "") or "").upper().split())
    if text:
        return f"{text}|{postal}"
    lat, lng = getattr(point, "lat", None), getattr(point, "lng", None)
    if lat is not None and lng is not None:
        return f"@{round(float(lat), 5)},{round(float(lng), 5)}|{postal}"
    return f"#{id(point)}"


_EMPTY: Parcel = (None, (None, None, None))


def merge_same_address(
    points: list[Any], buckets: list[list[Parcel]], item_keys: list[list[str | None]]
) -> tuple[list[Any], list[list[Parcel]], list[list[str | None]]]:
    """Drops entered twice for one delivery address become one destination."""
    seen: dict[str, int] = {}
    out_points: list[Any] = []
    out_buckets: list[list[Parcel]] = []
    out_keys: list[list[str | None]] = []
    for point, bucket, keys in zip(points, buckets, item_keys):
        addr = _address_key(point)
        if addr in seen:
            i = seen[addr]
            for box, key in zip(bucket, keys):
                if box != _EMPTY:
                    if out_buckets[i] == [_EMPTY]:
                        out_buckets[i], out_keys[i] = [], []
                    out_buckets[i].append(box)
                    out_keys[i].append(key)
            continue
        seen[addr] = len(out_points)
        out_points.append(point)
        out_buckets.append(list(bucket))
        out_keys.append(list(keys))
    return out_points, out_buckets, out_keys


def combine_boxes(bucket: list[Parcel]) -> tuple[Parcel, dict[str, Any]]:
    """
    Every box to one address as ONE consignment: weights add up, boxes stack.

    Stacked size = longest box length × widest box width × summed heights (each
    box's sides sorted longest first). Boxes stack, so the footprint the handling
    tier reads is the largest box's two longest sides, not the stack height.
    Volume is the sum of box volumes.
    """
    known = [(w, d) for w, d in bucket if w is not None or any(x for x in d)]
    boxes = len([p for p in bucket if p != (None, (None, None, None))]) or 1
    weights = [float(w) for w, _ in known if w]
    total_kg = round(sum(weights), 3) if weights else None
    sized = [sorted((float(x) for x in d if x), reverse=True) for _, d in known]
    sized = [s for s in sized if len(s) >= 2]
    dims: tuple[float | None, float | None, float | None] = (None, None, None)
    volume_cm3 = None
    stacked = None
    if sized:
        dims = (max(s[0] for s in sized), max(s[1] for s in sized), None)
    if sized and len(sized) == len(known) and all(len(s) == 3 for s in sized):
        stacked = (dims[0], dims[1], sum(s[2] for s in sized))
        volume_cm3 = round(sum(s[0] * s[1] * s[2] for s in sized), 1)
    info = {
        "boxes": boxes,
        "combined_weight_kg": total_kg,
        "combined_dimensions_cm": None if stacked is None else [round(x, 1) for x in stacked],
        "combined_volume_m3": None if volume_cm3 is None else round(volume_cm3 / 1_000_000, 4),
    }
    return (total_kg, dims), info


def _box_summary(info: dict[str, Any]) -> str:
    n = info["boxes"]
    bits = [f"{n} box{'es' if n != 1 else ''}"]
    if info.get("combined_weight_kg"):
        bits.append(f"{info['combined_weight_kg']:g} kg")
    if info.get("combined_volume_m3"):
        bits.append(f"{info['combined_volume_m3']:g} m³")
    return ", ".join(bits)


def _refuse(reason: str, stops: list[dict[str, Any]], schedule: ContractSchedule) -> ComponentQuote:
    return ComponentQuote(
        component=COMPONENT,
        metadata={
            "refused": True,
            "custom_quote_reason": reason,
            "custom_quote_stops": stops,
            "contract_schedule": schedule.id,
        },
    )


def _fsa_problem(fsa: str, schedule: ContractSchedule) -> str:
    if not fsa:
        return "no_destination_fsa"
    if fsa[1] == "0":
        return "rural_fsa"
    if fsa in schedule.custom_quote_fsas:
        return "custom_quote_fsa"
    return "unlisted_fsa"


class ContractRouteService:
    """Prices a whole route from a contract schedule."""

    def quote(
        self,
        request: PricingRequest,
        schedule: ContractSchedule,
    ) -> ComponentQuote:
        points = [request.dropoff, *(request.additional_stops or [])]
        fsas = [fsa_from_point(p) for p in points]
        buckets = parcels_by_stop(request)
        item_keys = keys_by_stop(request, buckets)
        if schedule.consolidate_per_destination:
            points, buckets, item_keys = merge_same_address(points, buckets, item_keys)
            fsas = [fsa_from_point(p) for p in points]

        # Whole-route refusal first, independent of stop order.
        bad = [
            {"stop": i + 1, "fsa": fsa or None, "reason": _fsa_problem(fsa, schedule)}
            for i, fsa in enumerate(fsas)
            if schedule.van_tier(fsa) is None
        ]
        if bad:
            return _refuse(bad[0]["reason"], bad, schedule)

        vehicle = str(request.vehicle_class or "").lower()
        downgraded = ""
        if vehicle in schedule.compact.vehicle_classes:
            downgraded = self._compact_blocker(schedule, fsas, buckets)
            if not downgraded:
                return self._compact(schedule, fsas, buckets, item_keys)
        quote = self._van(schedule, fsas, buckets, item_keys)
        if downgraded and not quote.metadata.get("refused"):
            quote.metadata["compact_downgraded"] = downgraded
        return quote

    def _compact_blocker(
        self, schedule: ContractSchedule, fsas: list[str], buckets: list[list[Parcel]]
    ) -> str:
        """Why this load cannot be compact, or "" when it can."""
        if any(not schedule.in_compact_territory(fsa) for fsa in fsas):
            return "outside_compact_territory"
        for bucket in buckets:
            for _weight, dims in bucket:
                fp = footprint_cm(dims)
                # Unknown size on an explicit compact request: trust the sender.
                if fp is not None and not fits(fp, schedule.compact.max_packed_cm):
                    return "parcel_over_compact_size"
        return ""

    def _groups(
        self, schedule: ContractSchedule, bucket: list[Parcel], keys: list[str | None]
    ) -> list[list[Parcel]]:
        """Parcels at one address: one item's boxes combined (owner rule), else one per box."""
        if schedule.consolidate_per_destination:
            return parcel_groups(bucket, keys)
        return [[box] for box in bucket]

    def _compact(
        self,
        schedule: ContractSchedule,
        fsas: list[str],
        buckets: list[list[Parcel]],
        item_keys: list[list[str | None]],
    ) -> ComponentQuote:
        terms = schedule.compact
        groups = [self._groups(schedule, b, k) for b, k in zip(buckets, item_keys)]
        stops = sum(terms.billable_stops(len(g)) for g in groups)
        band = terms.band_for(stops)
        items: list[PriceLineItem] = []
        if band.pickup_cents:
            items.append(PriceLineItem("compact_pickup", "Compact pickup", band.pickup_cents))
        stop_total = stops * band.stop_cents
        boxes = sum(len(b) for b in buckets)
        items.append(
            PriceLineItem(
                "compact_stop",
                f"Compact delivery ({stops} stop{'s' if stops != 1 else ''} × ${band.stop_cents / 100:g}"
                f" · {len(buckets)} address{'es' if len(buckets) != 1 else ''}, "
                f"{sum(len(g) for g in groups)} parcel(s), {boxes} box{'es' if boxes != 1 else ''})",
                stop_total,
            )
        )
        true_bill = band.pickup_cents + stop_total
        top_up = max(terms.route_minimum_cents - true_bill, 0)
        if top_up:
            items.append(PriceLineItem("route_minimum", "Compact route minimum", top_up))
        return ComponentQuote(
            component=COMPONENT,
            items=items,
            metadata={
                "contract_schedule": schedule.id,
                "contract_vehicle": "compact",
                "compact_banding": True,
                "compact_billable_stops": stops,
                "compact_parcel_count": sum(len(g) for g in groups),
                "compact_box_count": boxes,
                "consolidated_per_destination": schedule.consolidate_per_destination,
                "contract_destinations": fsas,
                "lift_flags": _lift_flags(fsas, buckets),
                "true_bill_cents": true_bill,
                "route_minimum_cents": terms.route_minimum_cents,
                "route_minimum_top_up_cents": top_up,
            },
        )

    def _van(
        self,
        schedule: ContractSchedule,
        fsas: list[str],
        buckets: list[list[Parcel]],
        item_keys: list[list[str | None]],
    ) -> ComponentQuote:
        items = [PriceLineItem("route_pickup", "Route pickup (Milton)", schedule.pickup_cents)]
        rows: list[dict[str, Any]] = []
        highest = None
        for idx, (fsa, bucket, keys) in enumerate(zip(fsas, buckets, item_keys), start=1):
            tier = schedule.van_tier(fsa)
            if tier is None:  # unreachable: quote() refuses unpriced stops first
                return _refuse(_fsa_problem(fsa, schedule), [{"stop": idx, "fsa": fsa}], schedule)
            if highest is None or tier.route_minimum_cents > highest.route_minimum_cents:
                highest = tier
            units, small, handling_cents = 0, 0, 0
            parcels_info: list[dict[str, Any]] = []
            for group in self._groups(schedule, bucket, keys):
                (weight, dims), info = combine_boxes(group)
                handling = schedule.handling_tier(weight, dims)
                over = False
                if handling is None:
                    if schedule.handling_beyond_extra_cents is None:
                        return _refuse(
                            "handling_beyond_schedule",
                            [{"stop": idx, "fsa": fsa, "reason": "handling_beyond_schedule"}],
                            schedule,
                        )
                    handling, over = schedule.handling[-1], True
                surcharge = handling.surcharge_cents + ((schedule.handling_beyond_extra_cents or 0) if over else 0)
                code = "handling_3" if over else handling.code
                info.update({"handling_tier": code, "handling_cents": surcharge})
                parcels_info.append(info)
                fp = footprint_cm(dims)
                if surcharge:
                    units += 1
                    handling_cents += surcharge
                    label = _HANDLING_LABELS.get(code, code)
                    if over:
                        label += f" (Tier 2 ${handling.surcharge_cents / 100:g} + ${(schedule.handling_beyond_extra_cents or 0) / 100:g})"
                    items.append(
                        PriceLineItem(
                            "handling",
                            f"{label} — stop {idx} {fsa} · {_box_summary(info)}",
                            surcharge,
                        )
                    )
                elif len(group) == 1 and fp is not None and fits(fp, schedule.group_max_cm):
                    small += 1
                else:
                    units += 1
            units += math.ceil(small / max(schedule.group_parcels_per_stop, 1))
            stop_cents = units * tier.stop_cents
            n_parcels, n_boxes = len(parcels_info), len(bucket)
            if schedule.consolidate_per_destination:
                label = (
                    f"Stop {idx} {fsa} · {tier.code} ${tier.stop_cents / 100:g}/stop — "
                    f"{n_parcels} parcel{'s' if n_parcels != 1 else ''}, {n_boxes} box{'es' if n_boxes != 1 else ''}"
                    + (f" → {units} billable stops" if units != 1 else "")
                )
            else:
                label = f"Stop {idx} {fsa} · {tier.code}" + (f" ({units} stops)" if units != 1 else "")
            items.append(PriceLineItem("contract_stop", label, stop_cents))
            total_kg = [p["combined_weight_kg"] for p in parcels_info if p.get("combined_weight_kg")]
            rows.append(
                {
                    "stop": idx,
                    "fsa": fsa,
                    "tier": tier.code,
                    "stop_rate_cents": tier.stop_cents,
                    "parcels": n_parcels,
                    "boxes": n_boxes,
                    "billable_stops": units,
                    "stop_cents": stop_cents,
                    "handling_cents": handling_cents,
                    "combined_weight_kg": round(sum(total_kg), 3) if total_kg else None,
                    "parcel_detail": parcels_info,
                }
            )
        true_bill = sum(i.amount_cents for i in items)
        minimum = highest.route_minimum_cents if highest else 0
        top_up = max(minimum - true_bill, 0)
        if top_up and highest:
            items.append(
                PriceLineItem("route_minimum", f"Route minimum top-up ({highest.code} minimum ${minimum / 100:g})", top_up)
            )
        return ComponentQuote(
            component=COMPONENT,
            items=items,
            metadata={
                "contract_schedule": schedule.id,
                "contract_vehicle": "cargo_van",
                "contract_stops": rows,
                "consolidated_per_destination": schedule.consolidate_per_destination,
                "lift_flags": _lift_flags(fsas, buckets),
                "fsa_tier": highest.code if highest else None,
                "origin_pickup_cents": schedule.pickup_cents,
                "true_bill_cents": true_bill,
                "route_minimum_cents": minimum,
                "route_minimum_top_up_cents": top_up,
            },
        )


_HANDLING_LABELS = {
    "handling_1": "Heavy-item handling Tier 1",
    "handling_2": "Heavy-item handling Tier 2",
    "handling_3": "Heavy-item handling Tier 3 (over Tier 2 limits)",
}
#: Term 05: a single driver will not lift a packed piece over 50 lb.
TWO_PERSON_KG = 50 * 0.45359237


def _lift_flags(fsas: list[str], buckets: list[list[Parcel]]) -> list[dict[str, Any]]:
    """Boxes over 50 lb (judged per box, never combined) → two-person handling note."""
    out = []
    for idx, (fsa, bucket) in enumerate(zip(fsas, buckets), start=1):
        heavy = [round(w, 1) for w, _d in bucket if w and w > TWO_PERSON_KG + 1e-6]
        if heavy:
            out.append({
                "stop": idx, "fsa": fsa, "boxes_over_50_lb": len(heavy), "box_weights_kg": heavy,
                "note": f"Stop {idx}: {len(heavy)} box(es) over 50 lb — two-person handling / equipment (Term 05).",
            })
    return out
