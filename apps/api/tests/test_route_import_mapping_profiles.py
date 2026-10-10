"""Load a saved CSV column mapping onto the next upload."""

from __future__ import annotations

from unittest.mock import patch
from uuid import uuid4

from porterchain_api.domain.merchant_states import MerchantRole, MerchantStatus
from porterchain_api.merchant_engine.import_column_mapper import (
    adapt_mapping_to_headers,
    apply_mapping,
)
from porterchain_api.merchant_engine.import_geocode import GeocodeResult
from porterchain_api.merchant_engine.import_mapping_profiles import (
    get_profile,
    save_profile,
)
from porterchain_api.merchant_engine.rbac import MerchantContext
from porterchain_api.merchant_engine.route_import_service import (
    MerchantRouteImportService,
    route_import_error_message,
)
from porterchain_api.merchant_models import Merchant, MerchantUser


def test_adapt_mapping_matches_headers_case_insensitively() -> None:
    adapted = adapt_mapping_to_headers(
        [{"canonical": "address", "source": "Ship_To", "confidence": 1}],
        ["ship_to", "name"],
    )
    assert adapted[0]["source"] == "ship_to"
    assert adapted[0]["confidence"] == 1.0


def test_apply_mapping_reads_case_insensitive_columns() -> None:
    rows = apply_mapping(
        [{"Ship To": "100 King St W"}],
        [{"canonical": "address", "source": "ship_to"}],
    )
    assert rows[0]["address"] == "100 King St W"


def test_english_mapping_errors() -> None:
    assert "not found" in route_import_error_message("mapping_profile_not_found").lower()
    assert "save" in route_import_error_message("route_import_no_mapping_to_save").lower()


def _ctx(db) -> MerchantContext:
    suffix = uuid4().hex[:8]
    merchant = Merchant(
        company_name=f"CSV Co {suffix}",
        email=f"csv-{suffix}@test.local",
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


def _geo(raw: str) -> GeocodeResult:
    return GeocodeResult(
        lat=43.65,
        lng=-79.38,
        formatted=raw,
        status="ok",
        confidence=0.9,
        unit=None,
        raw=raw,
        geocode_query=raw,
        issues=[],
    )


def test_upload_uses_named_saved_mapping(db) -> None:
    ctx = _ctx(db)
    mapping = [
        {"canonical": "address", "source": "location", "confidence": 1},
        {"canonical": "stop_type", "source": "kind", "confidence": 1},
    ]
    saved = save_profile(
        db,
        ctx.merchant,
        name="Shopify export",
        headers=["location", "kind"],
        mapping=mapping,
    )
    db.refresh(ctx.merchant)
    assert get_profile(ctx.merchant, saved["id"])["name"] == "Shopify export"

    csv = b"location,kind\n100 King St W,pickup\n200 Bay St,drop\n"
    svc = MerchantRouteImportService()
    with (
        patch(
            "porterchain_api.merchant_engine.import_quote.geocode_stop",
            side_effect=lambda **kw: _geo(str(kw.get("address") or "")),
        ),
        patch(
            "porterchain_api.merchant_engine.route_import_service.MerchantRouteImportService._quote_if_ready",
            return_value={"amount_cents": 1000, "currency": "cad"},
        ),
    ):
        job = svc.create_from_file(
            db,
            ctx,
            filename="stops.csv",
            data=csv,
            vehicle_class="cargo_van",
            scheduled_at=None,
            mapping_profile_id=saved["id"],
        )
    assert job.job_config["mapping_profile_id"] == saved["id"]
    assert job.job_config["mapping_profile_name"] == "Shopify export"
    address = next(m for m in job.job_config["mapping"] if m["canonical"] == "address")
    assert address["source"] == "location"


def test_apply_saved_mapping_to_open_job(db) -> None:
    ctx = _ctx(db)
    mapping = [
        {"canonical": "address", "source": "dest", "confidence": 1},
        {"canonical": "stop_type", "source": "type", "confidence": 1},
    ]
    saved = save_profile(db, ctx.merchant, name="Dest file", headers=["dest", "type"], mapping=mapping)
    db.refresh(ctx.merchant)

    csv = b"dest,type\n1 King St W,pickup\n2 King St W,drop\n"
    svc = MerchantRouteImportService()
    with (
        patch(
            "porterchain_api.merchant_engine.import_quote.geocode_stop",
            side_effect=lambda **kw: _geo(str(kw.get("address") or "")),
        ),
        patch(
            "porterchain_api.merchant_engine.route_import_service.MerchantRouteImportService._quote_if_ready",
            return_value={"amount_cents": 1200, "currency": "cad"},
        ),
    ):
        job = svc.create_from_file(
            db,
            ctx,
            filename="other.csv",
            data=csv,
            vehicle_class="cargo_van",
            scheduled_at=None,
        )
        applied = svc.apply_mapping_profile(db, ctx, job.id, saved["id"])
    assert applied.job_config["mapping_profile_id"] == saved["id"]
    assert applied.job_config["mapping_profile_name"] == "Dest file"
    address = next(m for m in applied.job_config["mapping"] if m["canonical"] == "address")
    assert address["source"] == "dest"
