"""Labels + packages spine — QR round-trip, page count, dims pass-through."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from porterchain_api.merchant_engine.stop_cargo import (
    cargo_dims_for_pricing,
    cargo_rollup,
)
from porterchain_api.reporting.qr_codec import (
    InvalidLabelQr,
    decode_label_qr,
    encode_label_qr,
)
from porterchain_api.reporting.thermal_pdf import (
    LABEL_HEIGHT,
    LABEL_WIDTH,
    render_thermal_labels,
)


def test_qr_codec_round_trip():
    raw = encode_label_qr(
        order_id="ord-1",
        package_id="pkg-1",
        route_hint="R12",
        stop_sequence=3,
        cod_cents=4500,
    )
    assert raw == "LOGISTICSv1|ord-1|pkg-1|R12|3|4500"
    decoded = decode_label_qr(raw)
    assert decoded.order_id == "ord-1"
    assert decoded.package_id == "pkg-1"
    assert decoded.route_hint == "R12"
    assert decoded.stop_sequence == "3"
    assert decoded.cod_cents == "4500"


def test_qr_codec_empty_cod_and_route():
    raw = encode_label_qr(order_id="o", package_id="p")
    assert raw == "LOGISTICSv1|o|p|||"
    decoded = decode_label_qr(raw)
    assert decoded.cod_cents == ""
    assert decoded.route_hint == ""


def test_qr_codec_rejects_bad_payload():
    with pytest.raises(InvalidLabelQr):
        decode_label_qr("BAD|a|b|c|d|e")
    with pytest.raises(InvalidLabelQr):
        decode_label_qr("LOGISTICSv1|only-two")


def test_thermal_pdf_page_count_and_media_box():
    pages = [
        {
            "route_hint": "A",
            "stop_sequence": 1,
            "from_line": "Warehouse",
            "to_line": "Customer",
            "order_number": "PC-1",
            "tracking_base": "TRK1",
            "cod_line": "$45.00",
            "qr_payload": encode_label_qr(order_id="o", package_id=f"p{i}", cod_cents=4500),
            "tracking_suffix": f"TRK1-{i:02d}",
            "parcel_index": i,
            "total_parcels": 3,
        }
        for i in range(1, 4)
    ]
    pdf = render_thermal_labels(pages)
    assert pdf.startswith(b"%PDF")
    assert b"/Count 3" in pdf
    assert abs(LABEL_WIDTH - 288) < 0.1
    assert abs(LABEL_HEIGHT - 432) < 0.1
    assert b"288 432" in pdf


def test_thermal_code128_renders_for_suffix() -> None:
    pdf = render_thermal_labels(
        [
            {
                "route_hint": "A",
                "stop_sequence": 1,
                "from_line": "WH",
                "to_line": "Cust",
                "order_number": "PC-1",
                "tracking_base": "TRK1",
                "cod_line": "—",
                "qr_payload": encode_label_qr(order_id="o", package_id="p1"),
                "tracking_suffix": "TRK1-01",
                "parcel_index": 1,
                "total_parcels": 1,
            }
        ]
    )
    assert pdf.startswith(b"%PDF")
    from porterchain_api.reporting.thermal_pdf import _draw_code128

    assert callable(_draw_code128)


def test_weight_only_body_seeds_pickup_package():
    from porterchain_api.merchant_engine.stop_cargo import (
        book_stops_for_request,
        packages_from_stops,
    )

    pickup = SimpleNamespace(formatted="123 Main St", lat=43.6, lng=-79.3, city=None, postal=None, name=None, phone=None, notes=None)
    dropoff = SimpleNamespace(formatted="456 Queen St", lat=43.65, lng=-79.39, city=None, postal=None, name=None, phone=None, notes=None)
    body = SimpleNamespace(
        weight_kg=12.5,
        package_type="looseParcel",
        packages=None,
        pickup=pickup,
        dropoff=dropoff,
        additional_stops=None,
        pickup_window_start=None,
        pickup_window_end=None,
    )
    stops = book_stops_for_request(body)
    pkgs = packages_from_stops(stops)
    assert len(pkgs) == 1
    assert pkgs[0]["weight_kg"] == 12.5


def test_cargo_dims_pass_through():
    body = SimpleNamespace(
        weight_kg=None,
        dimensions=None,
        packages=[
            SimpleNamespace(
                model_dump=lambda: {
                    "name": "Box",
                    "weight_kg": 12.5,
                    "length_cm": 40,
                    "width_cm": 30,
                    "height_cm": 20,
                }
            )
        ],
        pickup=SimpleNamespace(model_dump=dict, formatted="A", lat=1, lng=2),
        dropoff=SimpleNamespace(model_dump=dict, formatted="B", lat=3, lng=4),
        additional_stops=None,
        pickup_window_start=None,
        pickup_window_end=None,
    )
    # book_stops_for_request expects address fields via _addr_fields
    for addr in (body.pickup, body.dropoff):
        for k in ("formatted", "lat", "lng", "city", "postal", "name", "phone", "notes"):
            if not hasattr(addr, k):
                setattr(addr, k, None)
        addr.formatted = addr.formatted or "x"

    dims = cargo_dims_for_pricing(body)
    assert dims == {"length": 40.0, "width": 30.0, "height": 20.0}
    weight, rollup_dims = cargo_rollup(body)
    assert weight == 12.5
    assert rollup_dims == dims


def test_package_sync_three_boxes():
    from porterchain_api.merchant_engine.package_service import PackageService

    order = SimpleNamespace(
        id="ord-furniture",
        tracking_number="TRKFURN",
        compliance_metadata={
            "stops": [
                {
                    "id": "pu",
                    "sequence": 1,
                    "stop_type": "pickup",
                    "packages": [
                        {"name": "Sofa", "weight_kg": 40, "length_cm": 200, "width_cm": 90, "height_cm": 80},
                        {"name": "Chair", "weight_kg": 15, "length_cm": 60, "width_cm": 60, "height_cm": 90},
                        {"name": "Table", "weight_kg": 25, "length_cm": 120, "width_cm": 80, "height_cm": 40},
                    ],
                }
            ]
        },
    )
    added: list = []
    db = MagicMock()
    db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
    db.add.side_effect = lambda row: added.append(row)

    rows = PackageService().sync_from_order(db, order)  # type: ignore[arg-type]
    assert len(rows) == 3
    assert rows[0].total_parcels == 3
    assert rows[0].tracking_suffix == "TRKFURN-01"
    assert rows[2].tracking_suffix == "TRKFURN-03"
    assert rows[0].parcel_index == 1
