from enum import StrEnum


class MerchantStatus(StrEnum):
    PENDING = "PENDING"
    ONBOARDING = "ONBOARDING"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    CLOSED = "CLOSED"


#: Company statuses whose seats may open the merchant portal. Suspended and
#: closed are kicked out (AZ); pending has not been reviewed yet.
PORTAL_OPEN_STATUSES: frozenset[str] = frozenset(
    {MerchantStatus.ACTIVE.value, MerchantStatus.ONBOARDING.value}
)


class MerchantRole(StrEnum):
    """Porterchain merchant portal roles (merchant_users.role)."""
    OWNER = "merchant_owner"
    ADMIN = "merchant_admin"
    OPS = "merchant_ops"
    FINANCE = "merchant_finance"
    READONLY = "merchant_readonly"


# Portal display labels (user spec → canonical role)
PORTAL_ROLE_MAP: dict[str, MerchantRole] = {
    "owner": MerchantRole.OWNER,
    "manager": MerchantRole.ADMIN,
    "dispatcher": MerchantRole.OPS,
    "accounting": MerchantRole.FINANCE,
    "viewer": MerchantRole.READONLY,
}


class BulkImportStatus(StrEnum):
    UPLOADED = "UPLOADED"
    VALIDATING = "VALIDATING"
    PREVIEW = "PREVIEW"
    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"
