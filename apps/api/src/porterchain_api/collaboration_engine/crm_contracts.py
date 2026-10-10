"""CRM contracts and merchant conversion."""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from typing import Any

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from porterchain_api.collaboration_engine.crm_helpers import CrmActor
from porterchain_api.config import Settings
from porterchain_api.crm_models import (
    CrmActivity,
    CrmCompany,
    CrmContact,
    CrmContract,
    CrmDeal,
    CrmInvoice,
    CrmLead,
    CrmQuotation,
    CrmSalesTask,
)
from porterchain_api.domain.crm_states import (
    PIPELINE_STAGES,
    STAGE_PROBABILITY,
    CompanyMerchantStatus,
    ContractStatus,
    DealStage,
    LeadStatus,
    QuotationStatus,
    TaskStatus,
)
from porterchain_api.db_json import json_text, json_text_lower
from porterchain_api.collaboration_engine.crm_helpers import _actor, _now, _today, _to_int


class CrmContractsMixin:
    def list_contracts(
        self, db: Session, *, company_id: str | None = None, status: str | None = None, limit: int = 200
    ) -> list[CrmContract]:
        q = db.query(CrmContract)
        if company_id:
            q = q.filter(CrmContract.company_id == company_id)
        if status:
            q = q.filter(CrmContract.status == status)
        return q.order_by(CrmContract.created_at.desc()).limit(limit).all()

    def create_contract(self, db: Session, ctx: CrmActor | None, data: dict) -> CrmContract:
        contract = CrmContract(
            contract_number=self._next_number(db, CrmContract, "contract_number", "C"),
            created_by=_actor(ctx),
            **data,
        )
        db.add(contract)
        db.commit()
        db.refresh(contract)
        if contract.company_id:
            self.log_activity(
                db, entity_type="company", entity_id=contract.company_id, activity_type="system",
                subject=f"Contract {contract.contract_number} created", actor_id=_actor(ctx),
            )
        return contract

    def update_contract(self, db: Session, contract_id: str, data: dict) -> CrmContract:
        contract = db.get(CrmContract, contract_id)
        if not contract:
            raise LookupError("contract_not_found")
        for key, value in data.items():
            setattr(contract, key, value)
        db.commit()
        db.refresh(contract)
        return contract

    def convert_company_to_merchant(
        self,
        db: Session,
        ctx: CrmActor | None,
        company_id: str,
        settings: Settings | None = None,
    ) -> dict[str, Any]:
        company = db.get(CrmCompany, company_id)
        if not company:
            raise LookupError("company_not_found")
        if company.merchant_id:
            return {"merchant_id": company.merchant_id, "created": False, "invitation_sent": False}

        primary = (
            db.query(CrmContact)
            .filter(CrmContact.company_id == company.id, CrmContact.is_primary == True)  # noqa: E712
            .first()
        )
        email = (primary.email if primary else None) or company.email or ""
        prefs = [company.preferred_vehicle] if company.preferred_vehicle else []
        # Prefer catalog-valid prefs only (M-6); drop unknown class rather than fail convert.
        try:
            from porterchain_api.domain.retail_vehicles import validate_preferred_vehicles

            prefs = validate_preferred_vehicles(db, prefs)
        except ValueError:
            prefs = []

        from porterchain_api.merchant_engine.provision import create_onboarding_merchant

        merchant = create_onboarding_merchant(
            db,
            company_name=company.operating_name or company.legal_name,
            legal_name=company.legal_name,
            email=email,
            phone=company.phone,
            hst_number=company.hst_number,
            business_number=company.business_number,
            billing_address=company.billing_details or company.address or {},
            preferred_vehicles=prefs,
            profile={
                "crm_company_id": company.id,
                "industry": company.industry,
                "service_area": company.service_area,
                "estimated_deliveries_per_month": company.estimated_deliveries_per_month,
            },
        )

        company.merchant_id = merchant.id
        # M-20: not bookable until merchant ACTIVE — keep CRM in negotiating.
        company.merchant_status = CompanyMerchantStatus.NEGOTIATING.value
        db.commit()
        db.refresh(merchant)

        seat_added = False
        invitation_email = email
        if email:
            from porterchain_api.domain.merchant_states import MerchantRole
            from porterchain_api.merchant_engine.team_service import ensure_merchant_seat

            try:
                ensure_merchant_seat(
                    db,
                    merchant_id=merchant.id,
                    email=email,
                    role=MerchantRole.OWNER.value,
                    actor_user_id=_actor(ctx),
                    audit_action="merchant.owner_seat_added",
                )
                seat_added = True
            except Exception:
                seat_added = False

        self.log_activity(
            db,
            entity_type="company",
            entity_id=company.id,
            activity_type="status_change",
            subject="Converted to Porterchain merchant",
            metadata={"merchant_id": merchant.id, "owner_seat_email": email, "seat_added": seat_added},
            actor_id=_actor(ctx),
        )
        return {
            "merchant_id": merchant.id,
            "created": True,
            "seat_added": seat_added,
            "invitation_sent": seat_added,  # legacy key — seat reserved, no Clerk invite
            "invitation_email": email,
        }

# Re-exports kept for existing importers (integration).
from datetime import date  # noqa: E402, F401
from datetime import datetime  # noqa: E402, F401
from datetime import time  # noqa: E402, F401
from sqlalchemy import func  # noqa: E402, F401
from porterchain_api.crm_models import CrmActivity  # noqa: E402, F401
from porterchain_api.crm_models import CrmDeal  # noqa: E402, F401
from porterchain_api.crm_models import CrmInvoice  # noqa: E402, F401
from porterchain_api.crm_models import CrmLead  # noqa: E402, F401
from porterchain_api.crm_models import CrmQuotation  # noqa: E402, F401
from porterchain_api.crm_models import CrmSalesTask  # noqa: E402, F401
from porterchain_api.domain.crm_states import PIPELINE_STAGES  # noqa: E402, F401
from porterchain_api.domain.crm_states import STAGE_PROBABILITY  # noqa: E402, F401
from porterchain_api.domain.crm_states import ContractStatus  # noqa: E402, F401
from porterchain_api.domain.crm_states import DealStage  # noqa: E402, F401
from porterchain_api.domain.crm_states import LeadStatus  # noqa: E402, F401
from porterchain_api.domain.crm_states import QuotationStatus  # noqa: E402, F401
from porterchain_api.domain.crm_states import TaskStatus  # noqa: E402, F401
from porterchain_api.db_json import json_text  # noqa: E402, F401
from porterchain_api.db_json import json_text_lower  # noqa: E402, F401
from porterchain_api.collaboration_engine.crm_helpers import _now  # noqa: E402, F401
from porterchain_api.collaboration_engine.crm_helpers import _today  # noqa: E402, F401
from porterchain_api.collaboration_engine.crm_helpers import _to_int  # noqa: E402, F401
