"""CRM — leads, abandoned checkouts, tasks, notes."""

from sqlalchemy.orm import Session

from porterchain_api.admin_engine.rbac import AdminContext
from porterchain_api.admin_models import CrmNote, CrmTask
from porterchain_api.models import AbandonedCheckout, Lead, VisitorSession


class AdminCrmService:
    def pipeline_summary(self, db: Session) -> dict:
        leads = db.query(Lead).order_by(Lead.created_at.desc()).limit(100).all()
        abandoned = db.query(AbandonedCheckout).order_by(AbandonedCheckout.created_at.desc()).limit(50).all()
        visitors = db.query(VisitorSession).order_by(VisitorSession.created_at.desc()).limit(50).all()
        tasks = db.query(CrmTask).filter(CrmTask.status == "open").count()
        return {
            "visitor_leads": len(visitors),
            "quote_requests": len([l for l in leads if l.quote_id]),
            "abandoned_checkouts": len(abandoned),
            "business_inquiries": len([l for l in leads if l.source == "for_business"]),
            "open_tasks": tasks,
        }

    def list_leads(self, db: Session, *, limit: int = 50) -> list[Lead]:
        return db.query(Lead).order_by(Lead.created_at.desc()).limit(limit).all()

    def list_abandoned(self, db: Session, *, limit: int = 50) -> list[AbandonedCheckout]:
        return db.query(AbandonedCheckout).order_by(AbandonedCheckout.created_at.desc()).limit(limit).all()

    def list_tasks(self, db: Session, *, limit: int = 50) -> list[CrmTask]:
        return db.query(CrmTask).order_by(CrmTask.created_at.desc()).limit(limit).all()

    def create_task(
        self,
        db: Session,
        ctx: AdminContext,
        *,
        title: str,
        lead_id: str | None = None,
        merchant_id: str | None = None,
        due_at=None,
    ) -> CrmTask:
        task = CrmTask(
            title=title,
            lead_id=lead_id,
            merchant_id=merchant_id,
            due_at=due_at,
            assigned_to=ctx.user.id,
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        return task

    def add_note(
        self,
        db: Session,
        ctx: AdminContext,
        *,
        entity_type: str,
        entity_id: str,
        body: str,
    ) -> CrmNote:
        note = CrmNote(entity_type=entity_type, entity_id=entity_id, author_id=ctx.user.id, body=body)
        db.add(note)
        db.commit()
        db.refresh(note)
        return note

    def list_notes(self, db: Session, entity_type: str, entity_id: str) -> list[CrmNote]:
        return (
            db.query(CrmNote)
            .filter(CrmNote.entity_type == entity_type, CrmNote.entity_id == entity_id)
            .order_by(CrmNote.created_at.desc())
            .all()
        )
