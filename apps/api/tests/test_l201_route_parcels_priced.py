"""L201: a 117-drop route import must price 117 small parcels, not 1."""
from porterchain_api.merchant_engine.stop_cargo import route_parcel_rows, route_parcel_specs_from_dicts

BOX = {"weight_kg": 5.897, "length_cm": 35.56, "width_cm": 35.56, "height_cm": 21.59, "quantity": 1}


def test_rows_one_per_box_with_stop_index():
    drop = {"packages": [BOX]}
    extra = [{"packages": [BOX]} for _ in range(116)]
    rows = route_parcel_rows(drop, extra)
    assert len(rows) == 117
    assert rows[0]["stop_index"] == 0 and rows[-1]["stop_index"] == 116
    specs = route_parcel_specs_from_dicts(rows)
    assert len(specs) == 117 and specs[5].dimensions["length"] == 35.56


def test_parcel_price_117_small():
    from porterchain_pricing.three_models import parcel_price
    from porterchain_pricing.types import GeoPoint, PricingRequest

    specs = route_parcel_specs_from_dicts(route_parcel_rows({"packages": [BOX]}, [{"packages": [BOX]}] * 116))
    g = GeoPoint(lat=43.7, lng=-79.4)
    req = PricingRequest(pickup=g, dropoff=g, vehicle_class="cargo_van", parcels=specs, parcel_count=117)
    bd = parcel_price(req)
    assert bd.subtotal_cents == 117 * 600


def test_l202_zero_cargo_row_is_no_parcel():
    from porterchain_api.merchant_engine.import_rows import packages_from_row

    row = {"length": "0", "width": "0", "height": "0", "weight": "0", "dimensions_unit": "in", "weight_unit": "lbs"}
    assert packages_from_row(row, 1) == []
    assert len(packages_from_row({**row, "weight": "13", "sku": "WG-BOX"}, 2)) == 1
