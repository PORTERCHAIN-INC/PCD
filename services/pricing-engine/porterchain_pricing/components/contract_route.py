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


def merge_same_address(points: list[Any], buckets: list[list[Parcel]]) -> tuple[list[Any], list[list[Parcel]]]:
    """Drops entered twice for one delivery address become one destination."""
    keys: dict[str, int] = {}
    out_points: list[Any] = []
    out_buckets: list[list[Parcel]] = []
    for point, bucket in zip(points, buckets):
        key = _address_key(point)
        if key in keys:
            merged = out_buckets[keys[key]]
            merged.extend(p for p in bucket if p != (None, (None, None, None)))
            if not merged:
                merged.append((None, (None, None, None)))
            continue
        keys[key] = len(out_points)
        out_points.append(point)
        out_buckets.append(list(bucket))
    return out_points, out_buckets


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
    sized = [s for s in sized if len(s) == 3]
    dims: tuple[float | None, float | None, float | None] = (None, None, None)
    volume_cm3 = None
    stacked = None
    if sized and len(sized) == len(known):
        dims = (max(s[0] for s in sized), max(s[1] for s in sized), None)
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
        if schedule.consolidate_per_destination:
            points, buckets = merge_same_address(points, buckets)
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
                return self._compact(schedule, fsas, buckets)
        quote = self._van(schedule, fsas, buckets)
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

    def _compact(
        self, schedule: ContractSchedule, fsas: list[str], buckets: list[list[Parcel]]
    ) -> ComponentQuote:
        terms = schedule.compact
        if schedule.consolidate_per_destination:
            stops = len(buckets)  # one stop per delivery address, any number of boxes
        else:
            stops = sum(terms.billable_stops(len(bucket)) for bucket in buckets)
        band = terms.band_for(stops)
        items: list[PriceLineItem] = []
        if band.pickup_cents:
            items.append(PriceLineItem("compact_pickup", "Compact pickup", band.pickup_cents))
        stop_total = stops * band.stop_cents
        items.append(
            PriceLineItem(
                "compact_stop",
                f"Compact delivery ({stops} stop{'s' if stops != 1 else ''} × ${band.stop_cents / 100:g})",
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
                "compact_parcel_count": sum(len(b) for b in buckets),
                "consolidated_per_destination": schedule.consolidate_per_destination,
                "destinations": [
                    {"stop": i + 1, "fsa": f, **combine_boxes(b)[1]} for i, (f, b) in enumerate(zip(fsas, buckets))
                ],
                "contract_destinations": fsas,
                "true_bill_cents": true_bill,
                "route_minimum_cents": terms.route_minimum_cents,
                "route_minimum_top_up_cents": top_up,
            },
        )

    def _van(
        self, schedule: ContractSchedule, fsas: list[str], buckets: list[list[Parcel]]
    ) -> ComponentQuote:
        items = [PriceLineItem("route_pickup", "Route pickup", schedule.pickup_cents)]
        rows: list[dict[str, Any]] = []
        highest = None
        for idx, (fsa, bucket) in enumerate(zip(fsas, buckets), start=1):
            tier = schedule.van_tier(fsa)
            if tier is None:  # unreachable: quote() refuses unpriced stops first
                return _refuse(_fsa_problem(fsa, schedule), [{"stop": idx, "fsa": fsa}], schedule)
            if highest is None or tier.route_minimum_cents > highest.route_minimum_cents:
                highest = tier
            units, small, handling_cents = 0, 0, 0
            box_info: dict[str, Any] = {"boxes": len(bucket)}
            priced = bucket
            if schedule.consolidate_per_destination:
                combined, box_info = combine_boxes(bucket)
                priced = [combined]
            for weight, dims in priced:
                handling = schedule.handling_tier(weight, dims)
                if handling is None:
                    return _refuse(
                        "handling_beyond_schedule",
                        [{"stop": idx, "fsa": fsa, "reason": "handling_beyond_schedule"}],
                        schedule,
                    )
                fp = footprint_cm(dims)
                if handling.surcharge_cents:
                    units += 1
                    handling_cents += handling.surcharge_cents
                    items.append(
                        PriceLineItem(
                            "handling",
                            f"Heavy-item handling ({handling.code}) — stop {idx} {fsa}",
                            handling.surcharge_cents,
                        )
                    )
                elif not schedule.consolidate_per_destination and fp is not None and fits(
                    fp, schedule.group_max_cm
                ):
                    small += 1
                else:
                    units += 1
            units += math.ceil(small / max(schedule.group_parcels_per_stop, 1))
            stop_cents = units * tier.stop_cents
            if schedule.consolidate_per_destination:
                label = (
                    f"Stop {idx} {fsa} · {tier.code} — 1 stop ({_box_summary(box_info)})"
                    f" × ${tier.stop_cents / 100:g}"
                )
            else:
                label = f"Stop {idx} {fsa} · {tier.code}" + (f" ({units} stops)" if units != 1 else "")
            items.append(PriceLineItem("contract_stop", label, stop_cents))
            rows.append(
                {
                    "stop": idx,
                    "fsa": fsa,
                    "tier": tier.code,
                    "parcels": len(bucket),
                    "boxes": box_info["boxes"],
                    "combined_weight_kg": box_info.get("combined_weight_kg"),
                    "combined_dimensions_cm": box_info.get("combined_dimensions_cm"),
                    "combined_volume_m3": box_info.get("combined_volume_m3"),
                    "billable_stops": units,
                    "stop_cents": stop_cents,
                    "handling_cents": handling_cents,
                }
            )
        true_bill = sum(i.amount_cents for i in items)
        minimum = highest.route_minimum_cents if highest else 0
        top_up = max(minimum - true_bill, 0)
        if top_up and highest:
            items.append(PriceLineItem("route_minimum", f"Route minimum ({highest.code})", top_up))
        return ComponentQuote(
            component=COMPONENT,
            items=items,
            metadata={
                "contract_schedule": schedule.id,
                "contract_vehicle": "cargo_van",
                "contract_stops": rows,
                "consolidated_per_destination": schedule.consolidate_per_destination,
                "fsa_tier": highest.code if highest else None,
                "origin_pickup_cents": schedule.pickup_cents,
                "true_bill_cents": true_bill,
                "route_minimum_cents": minimum,
                "route_minimum_top_up_cents": top_up,
            },
        )
