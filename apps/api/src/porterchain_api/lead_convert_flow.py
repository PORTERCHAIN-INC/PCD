"""Lead → company / customer / driver_partner conversion flow (admin CRM)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.admin_engine.rbac import AdminContext
from porterchain_api.collaboration_engine.crm_service import CrmSalesService
from porterchain_api.config import Settings
from porterchain_api.crm_models import CrmLead


def convert_lead_with_outcome(
    db: Session,
    crm: CrmSalesService,
    ctx: AdminContext,
    lead: CrmLead,
    lead_id: str,
    *,
    body: Any,
    settings: Settings,
) -> dict[str, Any]:
    """Lead → company (+ deal); optional merchant / customer / driver_partner branch."""
    outcome = (body.outcome or lead.intent_type or "merchant").strip().lower()
    if outcome not in ("merchant", "retail_customer", "driver_partner"):
        outcome = "merchant"

    result = crm.convert_lead(
        db,
        ctx,
        lead_id,
        create_deal=body.create_deal if outcome == "merchant" else False,
        deal_name=body.deal_name,
        expected_revenue_cents=body.expected_revenue_cents,
        target_stage=body.target_stage,
    )

    out: dict[str, Any] = {**result, "to_merchant": body.to_merchant, "outcome": outcome}

    if outcome == "merchant" and body.to_merchant and result.get("company_id"):
        merchant = crm.convert_company_to_merchant(
            db, ctx, str(result["company_id"]), settings=settings
        )
        out["merchant"] = merchant

    lead = crm.get_lead(db, lead_id) or lead

    from porterchain_api.collaboration_engine.lead_scoring import clear_score_priors_cache

    clear_score_priors_cache()

    if outcome == "merchant" and lead.referred_by_merchant_id:
        from porterchain_api.collaboration_engine.lead_ops import grant_referral_credit

        credit = grant_referral_credit(
            db,
            lead=lead,
            company_id=result.get("company_id"),
            settings=settings,
        )
        if credit:
            db.commit()
            out["referral_credit"] = {
                "id": credit.id,
                "amount_cents": credit.amount_cents,
                "status": credit.status,
            }

    from porterchain_api.collaboration_engine.lead_capi import emit_lead_conversion_events

    out["capi"] = emit_lead_conversion_events(
        db, lead, event_name="LeadConverted", settings=settings
    )

    if outcome == "retail_customer" and lead.email:
        from porterchain_api.booking_engine.customer_service import CustomerService

        customer = CustomerService().ensure_from_email(
            db, email=lead.email, phone=lead.phone
        )
        db.commit()
        out["customer_id"] = customer.id
        crm.update_lead(
            db,
            lead_id,
            {
                "intent_type": "retail_customer",
                "decision_status": "converted",
                "status": "converted",
            },
        )
        crm.log_activity(
            db,
            entity_type="lead",
            entity_id=lead_id,
            activity_type="status_change",
            subject="Converted to retail customer",
            actor_id=ctx.user.id,
        )

    if outcome == "driver_partner":
        crm.update_lead(
            db,
            lead_id,
            {
                "intent_type": "driver_partner",
                "decision_status": "converted",
                "status": "converted",
                "tags": list({*(lead.tags or []), "driver_partner_converted"}),
            },
        )
        crm.create_task(
            db,
            ctx,
            {
                "title": f"Onboard driver partner: {lead.company_name}",
                "task_type": "follow_up",
                "entity_type": "lead",
                "entity_id": lead_id,
                "priority": "high",
            },
        )
        from porterchain_api.admin_engine.driver_service import AdminDriverService

        provisioned = AdminDriverService().provision_pending_from_lead(db, ctx, lead)
        out["driver_partner"] = {
            "queued": True,
            "hint": f"/drivers/{provisioned.id}",
            "driver_id": provisioned.id,
        }
        crm.log_activity(
            db,
            entity_type="lead",
            entity_id=lead_id,
            activity_type="status_change",
            subject="Converted to driver partner queue",
            actor_id=ctx.user.id,
        )

    return out


__all__ = ["convert_lead_with_outcome"]
