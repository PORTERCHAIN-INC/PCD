"""CRM sales tasks."""

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



class CrmTasksMixin:
    def list_tasks(
        self,
        db: Session,
        *,
        status: str | None = None,
        assigned_to: str | None = None,
        entity_type: str | None = None,
        entity_id: str | None = None,
        task_type: str | None = None,
        task_types: list[str] | None = None,
        due_after: datetime | None = None,
        due_before: datetime | None = None,
        limit: int = 300,
    ) -> list[CrmSalesTask]:
        q = db.query(CrmSalesTask)
        if status:
            q = q.filter(CrmSalesTask.status == status)
        if assigned_to:
            q = q.filter(CrmSalesTask.assigned_to == assigned_to)
        if entity_type:
            q = q.filter(CrmSalesTask.entity_type == entity_type)
        if entity_id:
            q = q.filter(CrmSalesTask.entity_id == entity_id)
        if task_type:
            q = q.filter(CrmSalesTask.task_type == task_type)
        if task_types:
            q = q.filter(CrmSalesTask.task_type.in_(task_types))
        if due_after:
            q = q.filter(CrmSalesTask.due_at >= due_after)
        if due_before:
            q = q.filter(CrmSalesTask.due_at <= due_before)
        return q.order_by(CrmSalesTask.due_at.asc().nullslast()).limit(limit).all()

    def get_task(self, db: Session, task_id: str) -> CrmSalesTask | None:
        return db.get(CrmSalesTask, task_id)

    def create_task(self, db: Session, ctx: CrmActor | None, data: dict) -> CrmSalesTask:
        data.setdefault("assigned_to", _actor(ctx))
        task = CrmSalesTask(created_by=_actor(ctx), **data)
        db.add(task)
        db.commit()
        db.refresh(task)
        return task

    def update_task(self, db: Session, task_id: str, data: dict) -> CrmSalesTask:
        task = db.get(CrmSalesTask, task_id)
        if not task:
            raise LookupError("task_not_found")
        for key, value in data.items():
            setattr(task, key, value)
        if data.get("status") == TaskStatus.DONE.value and not task.completed_at:
            task.completed_at = _now()
        db.commit()
        db.refresh(task)
        return task

    def delete_task(self, db: Session, task_id: str) -> None:
        task = db.get(CrmSalesTask, task_id)
        if not task:
            raise LookupError("task_not_found")
        db.delete(task)
        db.commit()

# Re-exports kept for existing importers (integration).
from datetime import date  # noqa: E402, F401
from datetime import time  # noqa: E402, F401
from sqlalchemy import func  # noqa: E402, F401
from porterchain_api.config import Settings  # noqa: E402, F401
from porterchain_api.crm_models import CrmActivity  # noqa: E402, F401
from porterchain_api.crm_models import CrmCompany  # noqa: E402, F401
from porterchain_api.crm_models import CrmContact  # noqa: E402, F401
from porterchain_api.crm_models import CrmContract  # noqa: E402, F401
from porterchain_api.crm_models import CrmDeal  # noqa: E402, F401
from porterchain_api.crm_models import CrmInvoice  # noqa: E402, F401
from porterchain_api.crm_models import CrmLead  # noqa: E402, F401
from porterchain_api.crm_models import CrmQuotation  # noqa: E402, F401
from porterchain_api.domain.crm_states import PIPELINE_STAGES  # noqa: E402, F401
from porterchain_api.domain.crm_states import STAGE_PROBABILITY  # noqa: E402, F401
from porterchain_api.domain.crm_states import CompanyMerchantStatus  # noqa: E402, F401
from porterchain_api.domain.crm_states import ContractStatus  # noqa: E402, F401
from porterchain_api.domain.crm_states import DealStage  # noqa: E402, F401
from porterchain_api.domain.crm_states import LeadStatus  # noqa: E402, F401
from porterchain_api.domain.crm_states import QuotationStatus  # noqa: E402, F401
from porterchain_api.db_json import json_text  # noqa: E402, F401
from porterchain_api.db_json import json_text_lower  # noqa: E402, F401
from porterchain_api.collaboration_engine.crm_helpers import _today  # noqa: E402, F401
from porterchain_api.collaboration_engine.crm_helpers import _to_int  # noqa: E402, F401
