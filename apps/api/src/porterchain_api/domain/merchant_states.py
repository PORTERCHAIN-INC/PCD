from enum import StrEnum


class MerchantStatus(StrEnum):
    PENDING = "PENDING"
    ONBOARDING = "ONBOARDING"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"


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


class MerchantPaymentTerms(StrEnum):
    IMMEDIATE = "IMMEDIATE"
    NET_7 = "NET_7"
    NET_14 = "NET_14"
    NET_15 = "NET_15"
    NET_30 = "NET_30"
    NET_45 = "NET_45"
    CUSTOM = "CUSTOM"


class BulkImportStatus(StrEnum):
    UPLOADED = "UPLOADED"
    VALIDATING = "VALIDATING"
    PREVIEW = "PREVIEW"
    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"
