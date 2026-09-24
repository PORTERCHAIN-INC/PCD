"""CRM — website leads, abandoned checkouts; tasks/notes live in collaboration_engine."""

from sqlalchemy.orm import Session

from porterchain_api.admin_engine.rbac import AdminContext
from porterchain_api.booking_models import AbandonedCheckout, VisitorSession
from porterchain_api.collaboration_engine import CrmSalesService
from porterchain_api.crm_models import CrmActivity, CrmLead, CrmSalesTask


class AdminCrmService:
    def __init__(self) -> None:
        self._sales = CrmSalesService()

    def pipeline_summary(self, db: Session) -> dict:
        leads = db.query(CrmLead).order_by(CrmLead.created_at.desc()).limit(100).all()
        abandoned = db.query(AbandonedCheckout).order_by(AbandonedCheckout.created_at.desc()).limit(50).all()
        visitors = db.query(VisitorSession).order_by(VisitorSession.created_at.desc()).limit(50).all()
        tasks = db.query(CrmSalesTask).filter(CrmSalesTask.status == "open").count()
        return {
            "visitor_leads": len(visitors),
            "quote_requests": len([l for l in leads if l.quote_id or l.source == "website_booking"]),
            "abandoned_checkouts": len(abandoned),
            "business_inquiries": len([l for l in leads if l.source == "for_business"]),
            "open_tasks": tasks,
        }

    def list_leads(self, db: Session, *, limit: int = 50) -> list[CrmLead]:
        return db.query(CrmLead).order_by(CrmLead.created_at.desc()).limit(limit).all()

    def list_abandoned(self, db: Session, *, limit: int = 50) -> list[AbandonedCheckout]:
        return db.query(AbandonedCheckout).order_by(AbandonedCheckout.created_at.desc()).limit(limit).all()

    def list_tasks(self, db: Session, *, limit: int = 50) -> list[CrmSalesTask]:
        return db.query(CrmSalesTask).order_by(CrmSalesTask.created_at.desc()).limit(limit).all()

    def create_task(
        self,
        db: Session,
        ctx: AdminContext,
        *,
        title: str,
        lead_id: str | None = None,
        merchant_id: str | None = None,
        due_at=None,
    ) -> CrmSalesTask:
        data: dict = {
            "title": title,
            "due_at": due_at,
            "assigned_to": ctx.user.id if ctx.user else None,
        }
        if lead_id:
            data["entity_type"] = "lead"
            data["entity_id"] = lead_id
        elif merchant_id:
            data["entity_type"] = "merchant"
            data["entity_id"] = merchant_id
        return self._sales.create_task(db, ctx, data)

    def add_note(
        self,
        db: Session,
        ctx: AdminContext,
        *,
        entity_type: str,
        entity_id: str,
        body: str,
    ) -> CrmActivity:
        return self._sales.log_activity(
            db,
            entity_type=entity_type,
            entity_id=entity_id,
            activity_type="note",
            body=body,
            actor_id=ctx.user.id if ctx.user else None,
        )

    def list_notes(self, db: Session, entity_type: str, entity_id: str) -> list[CrmActivity]:
        return self._sales.list_activities(db, entity_type=entity_type, entity_id=entity_id)
