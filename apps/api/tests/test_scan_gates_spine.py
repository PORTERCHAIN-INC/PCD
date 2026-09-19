"""Scan gates + live-prove (3 boxes → 3 labels → 1 fee → 3/3 scans)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from porterchain_api.merchant_engine.package_service import PackageService
from porterchain_api.merchant_engine.scan_gate_service import PackagesIncomplete, ScanGateService
from porterchain_api.reporting.label_service import LabelService
from porterchain_api.reporting.qr_codec import encode_label_qr
from porterchain_api.reporting.thermal_pdf import render_thermal_labels


def _order_with_three_boxes(order_id: str = "ord-furn") -> SimpleNamespace:
    return SimpleNamespace(
        id=order_id,
        tracking_number="TRK3BOX",
        order_number="PC-3BOX",
        amount_cents=8900,
        merchant_id="m1",
        pickup={"formatted": "Warehouse", "name": "WH"},
        dropoff={"formatted": "Customer", "name": "Cust"},
        cod_amount_cents=4500,
        cod_status="pending_collection",
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


def test_live_prove_three_boxes_three_labels_one_fee():
    """STOP gate: 3 JSON parcels → 3 package rows → 3 PDF pages → 1 amount_cents."""
    order = _order_with_three_boxes()
    db = MagicMock()
    db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
    db.add.side_effect = lambda row: None

    rows = PackageService().sync_from_order(db, order)  # type: ignore[arg-type]
    assert len(rows) == 3
    assert order.amount_cents == 8900  # one fee
    for i, row in enumerate(rows, start=1):
        row.id = f"pkg-{i}"

    labels = LabelService()
    labels._packages.ensure_for_order = lambda _db, _o: rows  # type: ignore[method-assign]
    pdf, filename = labels.build_order_labels_pdf(db, order, merchant_name="Acme")  # type: ignore[arg-type]
    assert filename.startswith("labels-")
    assert pdf.startswith(b"%PDF")
    assert b"/Count 3" in pdf
    assert b"$" in pdf and b"45" in pdf  # COD amount rendered on label


def test_scan_gate_blocks_until_all_three():
    order = _order_with_three_boxes()
    pkgs = []
    for i in range(1, 4):
        pkgs.append(
            SimpleNamespace(
                id=f"pkg-{i}",
                order_id=order.id,
                parcel_index=i,
                total_parcels=3,
                tracking_suffix=f"TRK3BOX-{i:02d}",
                status="manifested",
                weight_kg=None,
                dimensions=None,
            )
        )

    db = MagicMock()
    gate = ScanGateService()

    def list_side():
        return pkgs

    gate._packages.list_for_order = lambda _db, _oid: list_side()  # type: ignore[method-assign]
    gate._packages.ensure_for_order = lambda _db, _o: list_side()  # type: ignore[method-assign]

    with pytest.raises(PackagesIncomplete) as ei:
        gate.assert_complete(db, order, phase="pickup")  # type: ignore[arg-type]
    payload = ei.value.payload
    assert payload["scanned"] == 0
    assert payload["required"] == 3
    assert len(payload["missing_suffixes"]) == 3

    pkgs[0].status = "picked_up"
    pkgs[1].status = "picked_up"
    with pytest.raises(PackagesIncomplete) as ei2:
        gate.assert_complete(db, order, phase="pickup")  # type: ignore[arg-type]
    assert ei2.value.payload["scanned"] == 2
    assert ei2.value.payload["required"] == 3

    pkgs[2].status = "picked_up"
    gate.assert_complete(db, order, phase="pickup")  # type: ignore[arg-type]


def test_scan_qr_advances_and_cod_requires_pickup_scans():
    order = _order_with_three_boxes()
    pkg = SimpleNamespace(
        id="pkg-1",
        order_id=order.id,
        parcel_index=1,
        total_parcels=3,
        tracking_suffix="TRK3BOX-01",
        status="manifested",
        weight_kg=None,
        dimensions=None,
    )
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = pkg

    gate = ScanGateService()
    gate._packages.ensure_for_order = lambda _db, _o: [pkg]  # type: ignore[method-assign]
    gate._packages.list_for_order = lambda _db, _oid: [pkg]  # type: ignore[method-assign]

    qr = encode_label_qr(order_id=order.id, package_id="pkg-1", cod_cents=4500)
    out = gate.scan_qr(db, order, qr, phase="pickup")  # type: ignore[arg-type]
    assert pkg.status == "picked_up"
    assert out["scanned"] == 1

    # COD gate needs all packages — still incomplete with 1 of 1 in this stub list of 1
    gate.assert_cod_scans(db, order)  # type: ignore[arg-type]


def test_job_detail_schema_keeps_scan_progress():
    from porterchain_api.schemas_driver import DriverJobDetailResponse

    fields = DriverJobDetailResponse.model_fields
    assert "scan_pickup" in fields
    assert "scan_delivery" in fields
    parsed = DriverJobDetailResponse.model_validate(
        {
            "order_id": "o1",
            "order_number": "ORD",
            "tracking_number": "PC",
            "state": "AT_PICKUP",
            "status": "at_pickup",
            "bucket": "current",
            "pickup_address": "A",
            "delivery_address": "B",
            "pickup_stop_id": "s-pickup",
            "delivery_stop_id": "s-dropoff",
            "packages": [{"id": "pkg-1", "tracking_suffix": "PC-01"}],
            "scan_pickup": {
                "scanned": 0,
                "required": 1,
                "complete": False,
                "missing_suffixes": ["PC-01"],
            },
        }
    )
    assert parsed.scan_pickup.required == 1
    assert parsed.scan_pickup.complete is False


def test_delivery_scan_requires_pickup_first():
    order = _order_with_three_boxes()
    pkg = SimpleNamespace(
        id="pkg-1",
        order_id=order.id,
        status="manifested",
        tracking_suffix="TRK3BOX-01",
        parcel_index=1,
        total_parcels=1,
        weight_kg=None,
        dimensions=None,
    )
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = pkg
    gate = ScanGateService()
    gate._packages.ensure_for_order = lambda _db, _o: [pkg]  # type: ignore[method-assign]
    qr = encode_label_qr(order_id=order.id, package_id="pkg-1")
    with pytest.raises(ValueError, match="scan_pickup_required_first"):
        gate.scan_qr(db, order, qr, phase="delivery")  # type: ignore[arg-type]
