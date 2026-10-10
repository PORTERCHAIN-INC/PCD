"""AO — service area and assigned vehicles are admin-owned, not a merchant fleet."""

from __future__ import annotations

from types import SimpleNamespace

from porterchain_api.admin_engine.merchant_service import AdminMerchantService
from porterchain_api.crm_models import CrmCompany
from porterchain_api.domain.catalog_labels import vehicle_label
from porterchain_api.merchant_engine.booking_flow_service import (
    MerchantBookingFlowService,
)
from porterchain_api.merchant_engine.contacts_service import MerchantContactsService
from porterchain_api.merchant_engine.coverage import (
    COVERAGE_NOTE,
    DEFAULT_SERVICE_AREA,
    apply_coverage,
    coverage_snapshot,
)
from porterchain_api.merchant_engine.organization_sync import project_merchant_company
from porterchain_api.merchant_engine.profile_service import MerchantProfileService
from porterchain_api.merchant_engine.settings_service import MerchantSettingsService
from porterchain_api.schemas_merchant import MerchantProfileUpdateRequest


def test_empty_merchant_defaults_to_ontario() -> None:
    snap = coverage_snapshot(SimpleNamespace(preferred_vehicles=None, delivery_zones=None, profile=None))
    assert snap["service_area"] == DEFAULT_SERVICE_AREA
    assert snap["assigned_vehicles"] == []
    assert snap["delivery_zones"] == []
    assert snap["coverage_note"] == COVERAGE_NOTE


def test_assigned_vehicle_labels_are_english() -> None:
    assert vehicle_label("cargoVan") == "Cargo van"
    snap = coverage_snapshot(
        SimpleNamespace(preferred_vehicles=["cargoVan", "highRoof"], delivery_zones=[], profile={})
    )
    labels = {row["id"]: row["label"] for row in snap["assigned_vehicles"]}
    assert labels["cargoVan"] == "Cargo van"
    assert labels["highRoof"] == "Sprinter / high-roof"


def test_admin_apply_projects_service_area(db, admin_ctx, merchant_ctx) -> None:
    merchant_ctx.merchant.preferred_vehicles = ["cargoVan"]
    MerchantContactsService().ensure_company(db, merchant_ctx.merchant)
    db.commit()
    AdminMerchantService().update_merchant_terms(
        db,
        admin_ctx,
        merchant_ctx.merchant.id,
        delivery_zones=["gta_core"],
        service_area="Ontario — GTA",
    )
    db.refresh(merchant_ctx.merchant)
    snap = coverage_snapshot(merchant_ctx.merchant, db)
    assert snap["service_area"] == "Ontario — GTA"
    assert snap["assigned_vehicle_ids"] == ["cargoVan"]
    assert snap["assigned_vehicles"][0]["label"] == "Cargo van"
    assert snap["delivery_zones"][0]["code"] == "gta_core"
    assert snap["delivery_zones"][0]["name"] == "GTA Core"
    company = db.query(CrmCompany).filter(CrmCompany.merchant_id == merchant_ctx.merchant.id).one()
    assert company.service_area == "Ontario — GTA"


def test_apply_coverage_empty_clears_profile_area_not_crm(db, merchant_ctx) -> None:
    merchant = merchant_ctx.merchant
    apply_coverage(merchant, service_area="Ontario — East", delivery_zones=["gta_core"])
    project_merchant_company(db, merchant)
    db.commit()
    apply_coverage(merchant, service_area="", delivery_zones=[])
    db.commit()
    assert merchant.profile.get("service_area") is None
    assert not merchant.delivery_zones
    snap = coverage_snapshot(merchant, db)
    assert snap["service_area"] == "Ontario — East"
    assert snap["delivery_zones"] == []


def test_merchant_profile_patch_cannot_change_coverage(db, merchant_ctx) -> None:
    merchant_ctx.merchant.preferred_vehicles = ["cargoVan"]
    merchant_ctx.merchant.delivery_zones = ["gta_core"]
    merchant_ctx.merchant.profile = {"service_area": "Ontario — GTA"}
    db.commit()
    MerchantProfileService().update_profile(
        db,
        merchant_ctx,
        MerchantProfileUpdateRequest.model_validate(
            {
                "company_name": "Coverage Locked Inc.",
                "preferred_vehicles": ["sedan"],
                "delivery_zones": [],
                "service_area": "Quebec",
            }
        ),
    )
    db.refresh(merchant_ctx.merchant)
    assert merchant_ctx.merchant.company_name == "Coverage Locked Inc."
    assert merchant_ctx.merchant.preferred_vehicles == ["cargoVan"]
    assert merchant_ctx.merchant.delivery_zones == ["gta_core"]
    assert merchant_ctx.merchant.profile.get("service_area") == "Ontario — GTA"


def test_recommend_vehicle_includes_coverage_note() -> None:
    out = MerchantBookingFlowService().recommend_vehicle(
        SimpleNamespace(merchant=SimpleNamespace(preferred_vehicles=["cargoVan"])),
        weight_kg=80,
    )
    assert out["coverage_note"] == COVERAGE_NOTE
    assert out["service_area"] == DEFAULT_SERVICE_AREA
    assert out["assigned_vehicles"][0]["label"] == "Cargo van"


def test_settings_overview_includes_coverage(db, merchant_ctx) -> None:
    merchant_ctx.merchant.preferred_vehicles = ["cargoVan"]
    db.commit()
    overview = MerchantSettingsService().overview(db, merchant_ctx)
    coverage = overview["profile"]["coverage"]
    assert coverage["service_area"] == DEFAULT_SERVICE_AREA
    assert coverage["assigned_vehicles"][0]["label"] == "Cargo van"
    assert coverage["coverage_note"] == COVERAGE_NOTE
