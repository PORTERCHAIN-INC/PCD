"""Merchant sheets with a pickup and a dropoff address column become one routable job."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from porterchain_api.booking_engine.numbers import generate_order_number, generate_tracking_number
from porterchain_api.booking_engine.repositories.order_repository import OrderRepository
from porterchain_api.booking_models import Order
from porterchain_api.domain.merchant_states import MerchantStatus
from porterchain_api.domain.states import OrderState
from porterchain_api.merchant_engine import import_geocode
from porterchain_api.merchant_engine.import_column_mapper import (
    apply_mapping,
    mapping_confidence_ok,
    suggest_mapping,
)
from porterchain_api.merchant_engine.import_confirm import _address_input
from porterchain_api.merchant_engine.import_errors import route_import_error_message
from porterchain_api.merchant_engine.import_geocode import geocode_stop
from porterchain_api.merchant_engine.import_quote import resolve_stops
from porterchain_api.merchant_engine.import_rows import rows_to_stops
from porterchain_api.merchant_engine.stop_cargo import cargo_stop
from porterchain_api.merchant_models import Merchant

WAREHOUSE = "91 breton avenue mississauga l4z 4k5"


def _by(mapping):
    return {m.canonical: m for m in mapping}


# --- Column mapping ---


def test_pickup_and_dropoff_columns_both_map() -> None:
    mapping = suggest_mapping(["Pickup Address", "Dropoff Address", "Customer", "SKU", "Qty"])
    by = _by(mapping)
    assert by["pickup_address"].source == "Pickup Address"
    assert by["dropoff_address"].source == "Dropoff Address"
    assert by["address"].source is None
    assert mapping_confidence_ok(mapping)


def test_a_lone_delivery_column_is_still_the_address() -> None:
    mapping = suggest_mapping(["sequence", "type", "delivery_address"])
    by = _by(mapping)
    assert by["address"].source == "delivery_address"
    assert by["dropoff_address"].source is None
    assert mapping_confidence_ok(mapping)


def test_a_pickup_date_column_does_not_take_the_pickup_field() -> None:
    by = _by(suggest_mapping(["address", "pickup_date", "stop_type"]))
    assert by["address"].source == "address"
    assert by["pickup_address"].source is None


def test_confidence_gate_needs_both_halves_of_the_pair() -> None:
    only_pickup = [{"canonical": "pickup_address", "source": "from", "confidence": 1.0}]
    both = only_pickup + [{"canonical": "dropoff_address", "source": "to", "confidence": 1.0}]
    assert not mapping_confidence_ok(only_pickup)
    assert mapping_confidence_ok(both)


# --- Rows to stops ---


def _sheet_rows() -> list[dict]:
    headers = ["pickup_address", "dropoff_address", "customer", "order_id", "sku", "weight", "qty"]
    raw = [
        [WAREHOUSE, "200 Bay St, Toronto, ON M5J 2J2", "Ada", "SO-1", "BAG-1KG", "1", "2"],
        ["91 Breton Ave, Mississauga, L4Z 4K5", "10 Dundas St E, Toronto, ON", "Ben", "SO-2", "BAG-5KG", "5", "1"],
        [WAREHOUSE.upper(), "200 bay st, toronto, on m5j 2j2", "Ada", "SO-1", "MUG", "0.5", "1"],
    ]
    rows = [dict(zip(headers, r, strict=True)) for r in raw]
    return apply_mapping(rows, suggest_mapping(headers))


def test_every_row_shares_one_warehouse_pickup() -> None:
    stops = rows_to_stops(_sheet_rows())

    assert [s["stop_type"] for s in stops] == ["pickup", "drop", "drop"]
    assert [s["sequence"] for s in stops] == [1, 2, 3]
    assert stops[0]["address"] == WAREHOUSE
    assert stops[0]["packages"] == []


def test_same_dropoff_twice_is_one_stop_with_both_parcels() -> None:
    stops = rows_to_stops(_sheet_rows())
    ada = stops[1]

    assert ada["contact_name"] == "Ada"
    assert ada["external_ref"] == "SO-1"
    assert [p["sku"] for p in ada["packages"]] == ["BAG-1KG", "BAG-1KG", "MUG"]
    assert len({p["id"] for p in ada["packages"]}) == 3


def test_two_different_pickups_are_refused() -> None:
    rows = _sheet_rows()
    rows[1]["pickup_address"] = "100 King St W, Toronto, ON"

    with pytest.raises(ValueError, match="route_import_multiple_pickups"):
        rows_to_stops(rows)
    assert "more than one pickup" in route_import_error_message("route_import_multiple_pickups")


def test_one_address_column_sheet_is_unchanged() -> None:
    rows = [
        {"address": WAREHOUSE, "stop_type": "pickup", "sequence": "1"},
        {"address": "200 Bay St, Toronto", "stop_type": "drop", "sequence": "2"},
    ]
    stops = rows_to_stops(rows)
    assert [(s["stop_type"], s["address"]) for s in stops] == [
        ("pickup", WAREHOUSE),
        ("drop", "200 Bay St, Toronto"),
    ]


# --- Geocode: Nominatim only ---


@pytest.fixture
def no_cache():
    with (
        patch.object(import_geocode, "_cache_get", return_value=None),
        patch.object(import_geocode, "_cache_set"),
    ):
        yield


def test_nominatim_hit_stores_the_point(no_cache) -> None:
    hit = {"lat": "43.61", "lon": "-79.65", "display_name": "91 Breton Avenue"}
    with patch.object(import_geocode, "_nominatim_search", return_value=hit):
        geo = geocode_stop(address=WAREHOUSE)

    assert (geo.lat, geo.lng) == (43.61, -79.65)
    assert geo.status == "ok"
    assert geo.source == "nominatim"


def test_nominatim_miss_leaves_the_stop_failed(no_cache) -> None:
    with patch.object(import_geocode, "_nominatim_search", return_value=None):
        geo = geocode_stop(address=WAREHOUSE)

    assert geo.status == "failed"
    assert geo.lat is None


def test_postal_centroid_is_flagged_approximate(no_cache) -> None:
    def nominatim(query: str):
        if query.startswith("L4Z"):
            return {"lat": "43.60", "lon": "-79.60", "display_name": "L4Z"}
        return None

    with patch.object(import_geocode, "_nominatim_search", side_effect=nominatim):
        geo = geocode_stop(address="91 Breton Avenue", city="Mississauga", postal="L4Z 4K5")

    assert geo.status == "approximate"
    assert geo.source == "nominatim"
    assert "address.approximate" in geo.issues


def test_csv_coordinates_skip_nominatim(no_cache) -> None:
    with patch.object(import_geocode, "_nominatim_search") as search:
        geo = geocode_stop(address=WAREHOUSE, lat=43.6123, lng=-79.6543)

    search.assert_not_called()
    assert geo.status == "supplied"
    assert geo.source == "csv"
    assert (geo.lat, geo.lng) == (43.6123, -79.6543)
    assert geo.city == "Mississauga"
    assert geo.postal == "L4Z 4K5"


def test_places_supplied_keeps_formatted_and_source(no_cache) -> None:
    formatted = "91 Breton Ave, Mississauga, ON L4Z 4K5, Canada"
    with patch.object(import_geocode, "_nominatim_search") as search:
        geo = geocode_stop(
            address=formatted,
            lat=43.6123,
            lng=-79.6543,
            place_id="ChIJ-breton-91",
            source="places",
        )

    search.assert_not_called()
    assert geo.source == "places"
    assert geo.formatted == formatted
    assert geo.place_id == "ChIJ-breton-91"


def test_re_resolving_a_supplied_point_keeps_its_source() -> None:
    stop = {
        "sequence": 1,
        "stop_type": "pickup",
        "address": WAREHOUSE,
        "lat": 43.6123,
        "lng": -79.6543,
        "geocode_source": "csv",
    }
    resolved, _ = resolve_stops([stop], geocode_now=True)

    assert resolved[0]["geocode_source"] == "csv"
    assert (resolved[0]["lat"], resolved[0]["lng"]) == (43.6123, -79.6543)


def test_editing_an_address_drops_the_old_pin() -> None:
    from porterchain_api.merchant_engine.import_patch import patch_stop

    job = MagicMock(
        job_config={
            "stops": [
                {
                    "sequence": 2,
                    "stop_type": "drop",
                    "address": "200 Bay St, Toronto",
                    "lat": 43.64,
                    "lng": -79.38,
                    "geocode_source": "nominatim",
                    "geocode_status": "ok",
                }
            ]
        }
    )
    svc = MagicMock()
    svc.get_job.return_value = job
    svc._quote_if_ready.return_value = None

    patch_stop(svc, MagicMock(), MagicMock(), "job-1", 0, {"address": "10 Dundas St E, Toronto"})

    edited = job.job_config["stops"][0]
    assert edited["geocode_status"] == "pending"
    assert (edited["lat"], edited["lng"]) == (None, None)
    svc._enqueue_geocode.assert_called_once()


# --- Stored on the job ---


def test_confirmed_stop_and_address_keep_the_point() -> None:
    stop = {
        "sequence": 2,
        "stop_type": "drop",
        "formatted": "200 Bay St, Toronto, ON M5J 2J2",
        "lat": 43.64,
        "lng": -79.38,
        "geocode_source": "nominatim",
        "external_ref": "SO-1",
        "postal": "M5J 2J2",
    }
    fb = cargo_stop(stop)
    assert (fb["lat"], fb["lng"], fb["external_ref"]) == (43.64, -79.38, "SO-1")

    addr = _address_input(stop)
    assert (addr.lat, addr.lng, addr.postal) == (43.64, -79.38, "M5J 2J2")


def test_merchant_finds_the_job_by_their_row_reference(db) -> None:
    suffix = uuid4().hex[:8]
    merchant = Merchant(
        company_name=f"Roaster {suffix}",
        email=f"roaster-{suffix}@test.local",
        status=MerchantStatus.ACTIVE.value,
    )
    db.add(merchant)
    db.flush()
    order = Order(
        order_number=generate_order_number(),
        tracking_number=generate_tracking_number(),
        state=OrderState.BOOKED.value,
        merchant_id=merchant.id,
        amount_cents=2500,
        currency="cad",
        pickup={"formatted": WAREHOUSE},
        dropoff={"formatted": "200 Bay St, Toronto"},
        scheduled_at=datetime.now(UTC),
        compliance_metadata={
            "stops": [
                {"sequence": 1, "type": "pickup"},
                {"sequence": 2, "type": "dropoff", "external_ref": f"SO-{suffix}"},
            ]
        },
    )
    db.add(order)
    db.flush()

    repo = OrderRepository()
    found = repo.find_for_merchant_lookup(db, merchant.id, f"so-{suffix}")
    assert [o.id for o in found] == [order.id]
    assert repo.find_for_merchant_lookup(db, merchant.id, "SO-NOPE") == []
