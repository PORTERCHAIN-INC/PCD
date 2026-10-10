"""AI — route CSV errors use the same row + English message shape as classic bulk."""

from __future__ import annotations

from unittest.mock import patch
from uuid import uuid4

from porterchain_api.domain.merchant_states import MerchantRole, MerchantStatus
from porterchain_api.merchant_engine.import_geocode import GeocodeResult
from porterchain_api.merchant_engine.rbac import MerchantContext
from porterchain_api.merchant_engine.route_import_service import (
    MerchantRouteImportService,
    normalize_route_errors,
    route_import_error_message,
    route_row_error,
)
from porterchain_api.merchant_models import Merchant, MerchantUser


def test_route_row_errors_match_classic_bulk() -> None:
    row = route_row_error(row=2, code="stop.geocode_failed")
    assert row["row"] == 2
    assert row["error"] == "stop.geocode_failed"
    assert row["field"] == "address"
    assert "find this address" in row["message"].lower()
    assert "geocode" not in row["message"].lower()

    mapped = normalize_route_errors(
        [{"index": 0, "codes": ["stop.geocode_failed", "address.incomplete"]}]
    )
    assert [item["row"] for item in mapped] == [1, 1]
    assert mapped[0]["error"] == "stop.geocode_failed"
    assert "incomplete" in mapped[1]["message"].lower()
    assert "Could not confidently map" in route_import_error_message("mapping.address_low_confidence")


def _ctx(db) -> MerchantContext:
    suffix = uuid4().hex[:8]
    merchant = Merchant(
        company_name=f"CSV Err {suffix}",
        email=f"csverr-{suffix}@test.local",
        status=MerchantStatus.ACTIVE.value,
        profile={},
    )
    db.add(merchant)
    db.flush()
    user = MerchantUser(
        merchant_id=merchant.id,
        clerk_user_id=f"clerk_{suffix}",
        email=f"owner-{suffix}@test.local",
        role=MerchantRole.OWNER.value,
    )
    db.add(user)
    db.flush()
    return MerchantContext(merchant=merchant, user=user, role=MerchantRole.OWNER)


def _failed(raw: str) -> GeocodeResult:
    return GeocodeResult(
        lat=None,
        lng=None,
        formatted=None,
        status="failed",
        confidence=0.0,
        unit=None,
        raw=raw,
        geocode_query=raw,
        issues=["stop.geocode_failed"],
    )


def test_file_geocode_failure_uses_spreadsheet_row(db) -> None:
    ctx = _ctx(db)
    csv = b"address,stop_type\n100 King St W,pickup\nnowhere-zzz,drop\n"
    svc = MerchantRouteImportService()
    with (
        patch(
            "porterchain_api.merchant_engine.import_quote.geocode_stop",
            side_effect=lambda **kw: _failed(str(kw.get("address") or "")),
        ),
        patch(
            "porterchain_api.merchant_engine.route_import_service.MerchantRouteImportService._quote_if_ready",
            return_value=None,
        ),
    ):
        job = svc.create_from_file(
            db,
            ctx,
            filename="stops.csv",
            data=csv,
            vehicle_class="cargo_van",
            scheduled_at=None,
        )
        svc.apply_geocode_job(db, job.id)
        job = svc.get_job(db, ctx, job.id)
    assert job.error_rows >= 1
    first = job.errors[0]
    assert first["row"] == 2
    assert first["error"] == "stop.geocode_failed"
    assert "find this address" in first["message"].lower()
    payload = svc.job_response(job)
    assert payload["errors"][0]["row"] == 2
    assert payload["errors"][0]["message"]
