"""CRM quotations."""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from typing import Any

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from porterchain_api.config import Settings
from porterchain_api.crm_models import (
    CrmActivity,
    CrmCompany,
    CrmContact,
    CrmDeal,
    CrmInvoice,
    CrmLead,
    CrmSalesTask,
)
from porterchain_api.domain.crm_states import (
    PIPELINE_STAGES,
    STAGE_PROBABILITY,
    CompanyMerchantStatus,
    ContractStatus,
    DealStage,
    LeadStatus,
    TaskStatus,
)
from porterchain_api.db_json import json_text, json_text_lower
from porterchain_api.collaboration_engine.crm_helpers import _today, _to_int



class CrmQuotationsMixin:
    def _next_number(self, db: Session, model, attr: str, prefix: str) -> str:
        year = _today().year
        count = db.query(func.count()).select_from(model).scalar() or 0
        return f"{prefix}-{year}-{count + 1:04d}"

# Re-exports kept for existing importers (integration).
from datetime import date  # noqa: E402, F401
from datetime import datetime  # noqa: E402, F401
from datetime import time  # noqa: E402, F401
from porterchain_api.config import Settings  # noqa: E402, F401
from porterchain_api.crm_models import CrmActivity  # noqa: E402, F401
from porterchain_api.crm_models import CrmCompany  # noqa: E402, F401
from porterchain_api.crm_models import CrmContact  # noqa: E402, F401
from porterchain_api.crm_models import CrmDeal  # noqa: E402, F401
from porterchain_api.crm_models import CrmInvoice  # noqa: E402, F401
from porterchain_api.crm_models import CrmLead  # noqa: E402, F401
from porterchain_api.crm_models import CrmSalesTask  # noqa: E402, F401
from porterchain_api.domain.crm_states import PIPELINE_STAGES  # noqa: E402, F401
from porterchain_api.domain.crm_states import STAGE_PROBABILITY  # noqa: E402, F401
from porterchain_api.domain.crm_states import CompanyMerchantStatus  # noqa: E402, F401
from porterchain_api.domain.crm_states import ContractStatus  # noqa: E402, F401
from porterchain_api.domain.crm_states import DealStage  # noqa: E402, F401
from porterchain_api.domain.crm_states import LeadStatus  # noqa: E402, F401
from porterchain_api.domain.crm_states import TaskStatus  # noqa: E402, F401
from porterchain_api.db_json import json_text  # noqa: E402, F401
from porterchain_api.db_json import json_text_lower  # noqa: E402, F401
from porterchain_api.collaboration_engine.crm_helpers import _to_int  # noqa: E402, F401
