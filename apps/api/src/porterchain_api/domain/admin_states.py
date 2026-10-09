"""Admin platform roles per ROLE_PERMISSIONS.md."""

from enum import StrEnum


class AdminRole(StrEnum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    DISPATCHER = "dispatcher"
    SUPPORT = "support"
    SUPPORT_LEAD = "support_lead"
    SALES = "sales"
    SALES_MANAGER = "sales_manager"
    FINANCE = "finance"
    COMPLIANCE = "compliance"
    DEVELOPER = "developer"
    MARKETING = "marketing"
    READ_ONLY = "read_only"
    FLEET_MANAGER = "fleet_manager"


# User-facing labels → canonical role
PORTAL_ROLE_MAP: dict[str, AdminRole] = {
    "super_admin": AdminRole.SUPER_ADMIN,
    "admin": AdminRole.ADMIN,
    "dispatcher": AdminRole.DISPATCHER,
    "operations_manager": AdminRole.ADMIN,
    "fleet_manager": AdminRole.FLEET_MANAGER,
    "sales": AdminRole.SALES,
    "merchant_success": AdminRole.SALES,
    "support": AdminRole.SUPPORT,
    "customer_support": AdminRole.SUPPORT,
    "finance": AdminRole.FINANCE,
    "developer": AdminRole.DEVELOPER,
    "read_only": AdminRole.READ_ONLY,
    "auditor": AdminRole.READ_ONLY,
}


class DriverStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    SUSPENDED = "SUSPENDED"
    REJECTED = "REJECTED"


class ClaimStatus(StrEnum):
    OPEN = "open"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    CLOSED = "closed"


class TicketStatus(StrEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    ESCALATED = "escalated"
    RESOLVED = "resolved"
    CLOSED = "closed"
