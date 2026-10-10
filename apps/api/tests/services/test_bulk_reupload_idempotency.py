"""Bulk CSV re-upload protection: duplicate file warning + already-imported rows skipped."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from porterchain_api.domain.merchant_states import BulkImportStatus
from porterchain_api.merchant_engine.bulk_service import (
    MerchantBulkService,
    row_fingerprint,
)


def _csv(scheduled: str, ref: str = "") -> str:
    header = "pickup,dropoff,scheduled_at,internal_reference\n"
    return header + f"100 King St W Toronto,200 Bay St Toronto,{scheduled},{ref}\n"


def test_row_fingerprint_normalises_case_whitespace_and_uses_reference() -> None:
    a = {"pickup": "100 King St", "dropoff": "200 Bay St", "scheduled_at": "2026-10-10T09:00"}
    b = {"pickup": " 100  king st ", "dropoff": "200 BAY ST", "scheduled_at": "2026-10-10T09:00"}
    assert row_fingerprint(a) == row_fingerprint(b)
    assert row_fingerprint(a) != row_fingerprint({**a, "internal_reference": "PO-1"})
    assert row_fingerprint({**a, "internal_reference": "PO-1"}) != row_fingerprint(
        {**a, "internal_reference": "PO-2"}
    )


def test_in_file_duplicates_still_counted(db, merchant_ctx) -> None:
    scheduled = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    body = _csv(scheduled) + f"100 king st w toronto,200 Bay St Toronto,{scheduled},\n"
    job = MerchantBulkService().upload_csv(db, merchant_ctx, filename="dups.csv", content=body)
    assert job.duplicate_rows == 1
    assert any(e["error"] == "duplicate" for e in job.errors)


def test_reupload_warns_and_skips_already_booked_rows(db, merchant_ctx) -> None:
    svc = MerchantBulkService()
    scheduled = (datetime.now(UTC) + timedelta(days=2)).isoformat()
    content = _csv(scheduled, "PO-77")

    first = svc.upload_csv(db, merchant_ctx, filename="orders.csv", content=content)
    assert first.valid_rows == 1
    payload = svc.upload_payload(first)
    assert payload["warnings"] == []
    assert all("_fingerprint" not in row for row in payload["preview"])
    assert (first.job_config or {}).get("row_fingerprints")

    # Simulate the first job having been confirmed (confirm needs live pricing).
    first.status = BulkImportStatus.CONFIRMED.value
    db.commit()

    second = svc.upload_csv(db, merchant_ctx, filename="orders (1).csv", content=content)
    payload2 = svc.upload_payload(second)
    codes = {w["code"] for w in payload2["warnings"]}
    assert {"duplicate_file", "rows_already_imported"} <= codes
    assert second.valid_rows == 0
    assert second.duplicate_rows == 1
    assert second.errors[0]["error"] == "already_imported"
    assert second.errors[0]["prior_job_id"] == first.id

    # A genuinely new shipment in a later file is still accepted.
    other = svc.upload_csv(db, merchant_ctx, filename="new.csv", content=_csv(scheduled, "PO-78"))
    assert other.valid_rows == 1
    assert svc.upload_payload(other)["warnings"] == []


def test_preview_only_upload_does_not_block_rows(db, merchant_ctx) -> None:
    svc = MerchantBulkService()
    scheduled = (datetime.now(UTC) + timedelta(days=3)).isoformat()
    content = _csv(scheduled, "PO-90")
    svc.upload_csv(db, merchant_ctx, filename="a.csv", content=content)
    again = svc.upload_csv(db, merchant_ctx, filename="a.csv", content=content)
    # Same file re-uploaded before booking: warn, but rows are still bookable.
    assert again.valid_rows == 1
    assert [w["code"] for w in svc.upload_payload(again)["warnings"]] == ["duplicate_file"]
