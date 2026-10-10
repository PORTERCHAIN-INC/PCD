"""Driver-partner convert provisions one pending driver and does not enqueue Fleetbase."""

from __future__ import annotations

from uuid import uuid4

from porterchain_api.admin_engine.driver_service import AdminDriverService
from porterchain_api.admin_models import Driver
from porterchain_api.crm_models import CrmLead
from porterchain_api.domain.admin_states import DriverStatus


def test_provision_pending_from_lead_is_idempotent(db, admin_ctx):
    lead = CrmLead(
        company_name="Lane Partner",
        email=f"lane-{uuid4().hex[:8]}@example.com",
        source="website_driver_partner",
        intent_type="driver_partner",
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)

    svc = AdminDriverService()
    first = svc.provision_pending_from_lead(db, admin_ctx, lead)
    second = svc.provision_pending_from_lead(db, admin_ctx, lead)
    assert first.id == second.id
    assert first.status == DriverStatus.PENDING.value
    assert first.crm_lead_id == lead.id
    assert db.query(Driver).filter(Driver.crm_lead_id == lead.id).count() == 1
