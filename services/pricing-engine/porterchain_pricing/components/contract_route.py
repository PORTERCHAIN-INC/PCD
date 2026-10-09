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
            for weight, dims in bucket:
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
                elif fp is not None and fits(fp, schedule.group_max_cm):
                    small += 1
                else:
                    units += 1
            units += math.ceil(small / max(schedule.group_parcels_per_stop, 1))
            stop_cents = units * tier.stop_cents
            items.append(
                PriceLineItem(
                    "contract_stop",
                    f"Stop {idx} {fsa} · {tier.code}"
                    + (f" ({units} stops)" if units != 1 else ""),
                    stop_cents,
                )
            )
            rows.append(
                {
                    "stop": idx,
                    "fsa": fsa,
                    "tier": tier.code,
                    "parcels": len(bucket),
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
                "fsa_tier": highest.code if highest else None,
                "origin_pickup_cents": schedule.pickup_cents,
                "true_bill_cents": true_bill,
                "route_minimum_cents": minimum,
                "route_minimum_top_up_cents": top_up,
            },
        )
