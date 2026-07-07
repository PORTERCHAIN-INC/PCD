"""CRM domain states for the Porterchain Merchant CRM.

These power the logistics merchant acquisition pipeline: every business
inquiry becomes a lead, then a company + deal, and finally an active merchant.
"""

from enum import StrEnum


class LeadStatus(StrEnum):
    NEW = "new"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    UNQUALIFIED = "unqualified"
    NURTURING = "nurturing"
    CONVERTED = "converted"


class LeadPriority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class CompanyMerchantStatus(StrEnum):
    LEAD = "lead"
    PROSPECT = "prospect"
    NEGOTIATING = "negotiating"
    ACTIVE_MERCHANT = "active_merchant"
    CHURNED = "churned"


class DealStage(StrEnum):
    PROSPECTING = "prospecting"
    QUALIFIED = "qualified"
    MEETING_SCHEDULED = "meeting_scheduled"
    QUOTE_SENT = "quote_sent"
    NEGOTIATION = "negotiation"
    CONTRACT_REVIEW = "contract_review"
    WON = "won"
    LOST = "lost"
    HOLD = "hold"


# Ordered pipeline columns for the Kanban board.
PIPELINE_STAGES: list[str] = [
    DealStage.PROSPECTING.value,
    DealStage.QUALIFIED.value,
    DealStage.MEETING_SCHEDULED.value,
    DealStage.QUOTE_SENT.value,
    DealStage.NEGOTIATION.value,
    DealStage.CONTRACT_REVIEW.value,
    DealStage.WON.value,
    DealStage.LOST.value,
]

# Default win-probability suggestion per stage (percent).
STAGE_PROBABILITY: dict[str, int] = {
    DealStage.PROSPECTING.value: 10,
    DealStage.QUALIFIED.value: 25,
    DealStage.MEETING_SCHEDULED.value: 40,
    DealStage.QUOTE_SENT.value: 60,
    DealStage.NEGOTIATION.value: 75,
    DealStage.CONTRACT_REVIEW.value: 90,
    DealStage.WON.value: 100,
    DealStage.LOST.value: 0,
    DealStage.HOLD.value: 20,
}


class QuotationStatus(StrEnum):
    DRAFT = "draft"
    SENT = "sent"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CONVERTED = "converted"


class ContractStatus(StrEnum):
    DRAFT = "draft"
    PENDING_SIGNATURE = "pending_signature"
    ACTIVE = "active"
    EXPIRED = "expired"
    RENEWED = "renewed"
    TERMINATED = "terminated"


class ActivityType(StrEnum):
    NOTE = "note"
    CALL = "call"
    EMAIL = "email"
    MEETING = "meeting"
    SITE_VISIT = "site_visit"
    DEMO = "demo"
    STATUS_CHANGE = "status_change"
    DOCUMENT = "document"
    SYSTEM = "system"


class TaskType(StrEnum):
    CALL = "call"
    EMAIL = "email"
    MEETING = "meeting"
    FOLLOW_UP = "follow_up"
    DOCUMENT = "document"
    CONTRACT_REVIEW = "contract_review"
    MERCHANT_VISIT = "merchant_visit"
    DEMO = "demo"
    TODO = "todo"


class TaskStatus(StrEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    CANCELLED = "cancelled"


# Canonical contact roles for logistics merchant accounts.
CONTACT_ROLES: list[str] = [
    "decision_maker",
    "primary_contact",
    "influencer",
    "accounts_payable",
    "warehouse_manager",
    "shipping_manager",
    "operations_manager",
    "purchasing",
    "owner",
]
