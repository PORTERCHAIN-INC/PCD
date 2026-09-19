"""Order payload mapper contract — multi-stop / waypoint mapping.

Covers the four PorterChain order types:
  1. single pickup → single delivery (no waypoints)
  2. single pickup → multi delivery (hub & spoke)
  3. multi-pickup → multi-delivery
  4. legacy additional_stops path (backward compatibility)
"""

from __future__ import annotations

from porterchain_fleetbase_adapter.mappers import build_order_payload

PICKUP = {"formatted": "1 Depot Rd, Toronto", "lat": 43.65, "lng": -79.38, "city": "Toronto"}
DROP_A = {"formatted": "10 King St W, Toronto", "lat": 43.65, "lng": -79.39}
DROP_B = {"formatted": "20 Queen St E, Toronto", "lat": 43.66, "lng": -79.37}
DROP_C = {"formatted": "30 Bay St, Toronto", "lat": 43.64, "lng": -79.36}
PICKUP_B = {"formatted": "5 Warehouse Ave, Mississauga", "lat": 43.59, "lng": -79.64}

BASE_ORDER = {
    "porterchain_order_id": "ord_1",
    "order_number": "PC-1001",
    "tracking_number": "TRK-1001",
    "merchant_id": "merch_1",
}


def test_single_pickup_dropoff_has_no_waypoints():
    body = build_order_payload({**BASE_ORDER, "pickup": PICKUP, "dropoff": DROP_A})
    assert body["pickup"]["street1"] == PICKUP["formatted"]
    assert body["dropoff"]["street1"] == DROP_A["formatted"]
    assert body["pickup"]["location"] == {"type": "Point", "coordinates": [-79.38, 43.65]}
    assert "waypoints" not in body
    assert "stops" not in body["meta"]
    assert "entities" not in body
    assert body["meta"]["porterchain_order_id"] == "ord_1"


def test_hub_and_spoke_maps_intermediate_drops_to_waypoints():
    stops = [
        {"id": "s0", "type": "pickup", "sequence": 0, **PICKUP},
        {"id": "s1", "type": "dropoff", "sequence": 1, **DROP_A},
        {"id": "s2", "type": "dropoff", "sequence": 2, **DROP_B},
        {"id": "s3", "type": "dropoff", "sequence": 3, **DROP_C},
    ]
    body = build_order_payload({**BASE_ORDER, "stops": stops})
    assert body["pickup"]["street1"] == PICKUP["formatted"]
    # Last sequenced dropoff becomes the payload dropoff; the rest are waypoints.
    assert body["dropoff"]["street1"] == DROP_C["formatted"]
    assert [w["street1"] for w in body["waypoints"]] == [DROP_A["formatted"], DROP_B["formatted"]]
    assert [w["order"] for w in body["waypoints"]] == [0, 1]
    assert [w["_import_id"] for w in body["waypoints"]] == ["s1", "s2"]
    assert all(w["type"] == "dropoff" for w in body["waypoints"])
    assert len(body["meta"]["stops"]) == 4


def test_multi_pickup_multi_delivery_preserves_types_and_sequence():
    stops = [
        {"id": "s0", "type": "pickup", "sequence": 0, **PICKUP},
        {
            "id": "s1",
            "type": "pickup",
            "sequence": 1,
            "time_window_start": "2026-08-08T09:00:00Z",
            "time_window_end": "2026-08-08T11:00:00Z",
            "service_time_seconds": 600,
            "pod_required": True,
            **PICKUP_B,
        },
        {"id": "s2", "type": "dropoff", "sequence": 2, **DROP_A},
        {"id": "s3", "type": "dropoff", "sequence": 3, **DROP_B},
    ]
    body = build_order_payload({**BASE_ORDER, "stops": stops})
    assert body["pickup"]["street1"] == PICKUP["formatted"]
    assert body["dropoff"]["street1"] == DROP_B["formatted"]
    assert len(body["waypoints"]) == 2
    second_pickup = body["waypoints"][0]
    assert second_pickup["street1"] == PICKUP_B["formatted"]
    assert second_pickup["type"] == "pickup"
    assert second_pickup["time_window_start"] == "2026-08-08T09:00:00Z"
    assert second_pickup["service_time"] == 600
    assert second_pickup["pod_required"] is True
    # meta.stops preserves full fidelity including the intermediate pickup type.
    assert [s["type"] for s in body["meta"]["stops"]] == ["pickup", "pickup", "dropoff", "dropoff"]


def test_stops_are_sorted_by_sequence_before_mapping():
    stops = [
        {"id": "s2", "type": "dropoff", "sequence": 2, **DROP_B},
        {"id": "s0", "type": "pickup", "sequence": 0, **PICKUP},
        {"id": "s1", "type": "dropoff", "sequence": 1, **DROP_A},
    ]
    body = build_order_payload({**BASE_ORDER, "stops": stops})
    assert body["dropoff"]["street1"] == DROP_B["formatted"]
    assert body["waypoints"][0]["street1"] == DROP_A["formatted"]


def test_legacy_additional_stops_still_map_to_waypoints():
    body = build_order_payload(
        {**BASE_ORDER, "pickup": PICKUP, "dropoff": DROP_C, "additional_stops": [DROP_A, DROP_B]}
    )
    assert [w["street1"] for w in body["waypoints"]] == [DROP_A["formatted"], DROP_B["formatted"]]
    assert body["meta"]["additional_stops"] == body["waypoints"]


def test_packages_pin_to_waypoint_via_import_id():
    stops = [
        {"id": "s0", "type": "pickup", "sequence": 0, **PICKUP},
        {
            "id": "s1",
            "type": "dropoff",
            "sequence": 1,
            "packages": [{"id": "pkg_1", "name": "Box A", "weight_kg": 4.2, "quantity": 2}],
            **DROP_A,
        },
        {"id": "s2", "type": "dropoff", "sequence": 2, **DROP_B},
    ]
    body = build_order_payload({**BASE_ORDER, "stops": stops})
    assert len(body["entities"]) == 1
    entity = body["entities"][0]
    assert entity["name"] == "Box A"
    assert entity["weight"] == 4.2
    assert entity["quantity"] == 2
    # Stock Fleetbase places FK — never put import keys on destination_uuid.
    assert "destination_uuid" not in entity
    assert entity["meta"]["porterchain_package_id"] == "pkg_1"
    assert entity["meta"]["destination_import_id"] == "s1"
    assert entity["meta"]["porterchain_stop_id"] == "s1"


def test_uuid_stop_id_does_not_set_destination_uuid_fk():
    """Stock Fleetbase places FK must not receive PC stop UUIDs."""
    stop_uuid = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    stops = [
        {"id": "s0", "type": "pickup", "sequence": 0, **PICKUP},
        {
            "id": stop_uuid,
            "type": "dropoff",
            "sequence": 1,
            "packages": [{"id": "pkg_1", "name": "Box A", "weight_kg": 1.0}],
            **DROP_A,
        },
    ]
    body = build_order_payload({**BASE_ORDER, "stops": stops})
    entity = body["entities"][0]
    assert "destination_uuid" not in entity
    assert entity["meta"]["destination_import_id"] == stop_uuid
    assert entity["meta"]["porterchain_stop_id"] == stop_uuid


def test_order_level_packages_map_to_entities_with_dims():
    body = build_order_payload(
        {
            **BASE_ORDER,
            "pickup": PICKUP,
            "dropoff": DROP_A,
            "packages": [
                {
                    "id": "pkg_2",
                    "name": "Crate",
                    "weight_kg": 12.5,
                    "length_cm": 40,
                    "width_cm": 30,
                    "height_cm": 20,
                }
            ],
            "weight_kg": 12.5,
            "volume_m3": 0.024,
            "parcels": 1,
        }
    )
    assert len(body["entities"]) == 1
    entity = body["entities"][0]
    assert entity["weight"] == 12.5
    assert entity["length"] == 40
    assert entity["width"] == 30
    assert entity["height"] == 20
    assert entity["dimensions_unit"] == "cm"
    assert body["meta"]["weight_kg"] == 12.5
    assert body["meta"]["volume_m3"] == 0.024
    assert body["meta"]["parcels"] == 1


def test_vehicle_payload_maps_fleetbase_capacity_columns():
    from porterchain_fleetbase_adapter.mappers import build_vehicle_payload

    body = build_vehicle_payload(
        {
            "id": "pc-v1",
            "plate_number": "ABCD123",
            "make_model": "Ford Transit",
            "vehicle_class": "cargo_van",
            "capacity_kg": 900,
            "capacity_volume_m3": 8.5,
            "is_active": True,
        }
    )
    assert body["payload_capacity"] == 900
    assert body["capacity"] == 900
    assert body["payload_capacity_volume"] == 8.5
    assert body["payload_capacity_parcels"] == 100
    assert body["type"] == "cargo_van"


def test_company_uuid_and_optional_fields_pass_through():
    body = build_order_payload(
        {**BASE_ORDER, "pickup": PICKUP, "dropoff": DROP_A, "special_instructions": "Call first", "pod_required": True},
        company_uuid="co_1",
    )
    assert body["type"] == "transport"
    assert body["company_uuid"] == "co_1"
    assert body["notes"] == "Call first"
    assert body["pod_required"] is True
    assert body["internal_id"] == "PC-1001"


def test_driver_payload_omits_public_id_as_vehicle_uuid():
    from porterchain_fleetbase_adapter.mappers import build_driver_payload

    body = build_driver_payload(
        {
            "id": "pc-d1",
            "full_name": "Jordan Patel",
            "email": "jordan@example.com",
            "fleetbase_vehicle_id": "vehicle_vikeqgn6qz",
        },
        company_uuid="co_1",
    )
    assert "vehicle_uuid" not in body
    uuid_body = build_driver_payload(
        {"id": "pc-d1", "full_name": "Jordan Patel", "fleetbase_vehicle_id": "e136168f-516e-4b43-b6c2-ed4178169bce"}
    )
    assert uuid_body["vehicle_uuid"] == "e136168f-516e-4b43-b6c2-ed4178169bce"
