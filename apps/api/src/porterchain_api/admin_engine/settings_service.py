"""Enterprise System Settings Center — Application Service (masterrule §3).

Runtime business configuration is stored in SystemConfig. Secrets and infrastructure
endpoints remain in environment variables — the admin UI exposes status only, never secrets.
Module-specific settings (support SLA, pricing tax, reports) are owned by their modules;
this service surfaces them for read/link without duplicating write paths.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.audit import log_admin_audit
from porterchain_api.admin_engine.rbac import MODULE_PERMISSIONS, AdminContext
from porterchain_api.admin_models import AdminAuditLog, AdminUser, Driver, SystemConfig, Vehicle
from porterchain_api.admin_engine.clerk_directory_service import fetch_clerk_snapshots
from porterchain_api.auth.clerk_client import ClerkUserSnapshot
from porterchain_api.auth.clerk_registry import is_clerk_configured, is_clerk_secret_configured
from porterchain_api.auth.invitation_service import InvitationService
from porterchain_api.config import Settings
from porterchain_api.invitation_models import UserInvitation
from porterchain_api.merchant_models import Merchant, MerchantUser
from porterchain_api.models import Customer
from porterchain_api.schemas_admin import (
    PlatformUserAuthorizeResponse,
    PlatformUserItem,
    PlatformUsersFacets,
    PlatformUsersResponse,
)
from porterchain_api.domain.admin_states import DriverStatus
from porterchain_api.domain.merchant_states import MerchantStatus
from porterchain_shared.auth.enterprise_roles import EnterpriseRole
from porterchain_api.platform.health import readiness
from porterchain_shared.config.settings import PlatformSettings


PORTERCHAIN_VERSION = os.environ.get("PORTERCHAIN_VERSION", "3.1.0")

SETTINGS_SECTIONS: list[dict[str, str]] = [
    {"id": "dashboard", "label": "Dashboard", "group": "overview"},
    {"id": "general", "label": "General", "group": "company"},
    {"id": "branding", "label": "Branding", "group": "company"},
    {"id": "users", "label": "Users", "group": "access"},
    {"id": "roles", "label": "Roles & Permissions", "group": "access"},
    {"id": "authentication", "label": "Authentication", "group": "access"},
    {"id": "security", "label": "Security", "group": "access"},
    {"id": "notifications", "label": "Notifications", "group": "communications"},
    {"id": "email", "label": "Email", "group": "communications"},
    {"id": "sms", "label": "SMS", "group": "communications"},
    {"id": "push", "label": "Push Notifications", "group": "communications"},
    {"id": "fleetbase", "label": "Fleetbase", "group": "integrations"},
    {"id": "google_maps", "label": "Google Maps", "group": "integrations"},
    {"id": "stripe", "label": "Stripe", "group": "integrations"},
    {"id": "firebase", "label": "Firebase", "group": "integrations"},
    {"id": "storage", "label": "Storage", "group": "integrations"},
    {"id": "api_keys", "label": "API Keys", "group": "integrations"},
    {"id": "integrations", "label": "Integrations", "group": "integrations"},
    {"id": "vehicles", "label": "Vehicles", "group": "operations"},
    {"id": "service_areas", "label": "Service Areas", "group": "operations"},
    {"id": "delivery_zones", "label": "Delivery Zones", "group": "operations"},
    {"id": "booking", "label": "Booking", "group": "operations"},
    {"id": "merchant", "label": "Merchant", "group": "modules"},
    {"id": "driver", "label": "Driver", "group": "modules"},
    {"id": "customer", "label": "Customer", "group": "modules"},
    {"id": "operations", "label": "Operations", "group": "modules"},
    {"id": "finance", "label": "Finance", "group": "modules"},
    {"id": "documents", "label": "Documents", "group": "modules"},
    {"id": "claims", "label": "Claims", "group": "modules"},
    {"id": "support", "label": "Support", "group": "modules"},
    {"id": "reports", "label": "Reports", "group": "modules"},
    {"id": "automation", "label": "Automation", "group": "platform"},
    {"id": "feature_flags", "label": "Feature Flags", "group": "platform"},
    {"id": "audit", "label": "Audit", "group": "platform"},
    {"id": "backup", "label": "Backup", "group": "platform"},
    {"id": "logs", "label": "Logs", "group": "platform"},
    {"id": "maintenance", "label": "System Maintenance", "group": "platform"},
    {"id": "developer", "label": "Developer", "group": "platform"},
]

CONFIG_KEYS = {
    "general": "settings_general",
    "branding": "settings_branding",
    "authentication": "settings_authentication",
    "security": "settings_security",
    "notifications": "notification_templates",
    "booking": "settings_booking",
    "merchant": "settings_merchant",
    "driver": "settings_driver",
    "customer": "settings_customer",
    "finance": "settings_finance",
    "documents": "settings_documents",
    "claims": "settings_claims",
    "automation": "settings_automation",
    "feature_flags": "settings_feature_flags",
    "vehicles": "vehicle_types",
    "service_areas": "service_areas",
    "delivery_zones": "settings_delivery_zones",
    "package_types": "package_types",
    "integrations_meta": "integrations",
}

DEFAULTS: dict[str, Any] = {
    "settings_general": {
        "company_name": "Porterchain",
        "legal_name": "Porterchain Logistics Inc.",
        "timezone": "America/Toronto",
        "support_email": "support@porterchain.com",
        "business_hours": {"mon_fri": "08:00-18:00", "sat": "09:00-14:00"},
        "holidays": [],
    },
    "settings_branding": {
        "primary_color": "#2563eb",
        "secondary_color": "#0ea5e9",
        "typography": "Inter",
    },
    "settings_authentication": {
        "session_timeout_minutes": 480,
        "mfa_required": False,
        "allowed_domains": [],
    },
    "settings_security": {
        "rate_limit_per_minute": 120,
        "ip_allow_list": [],
        "password_min_length": 12,
    },
    "settings_booking": {
        "quote_ttl_minutes": 30,
        "booking_draft_ttl_minutes": 1440,
        "default_currency": "cad",
        "default_vehicle_class": "sedan",
        # ASAP / INSTANT promise window used by order SLA (not the same as scheduled_at).
        "instant_delivery_sla_hours": 4,
    },
    "settings_merchant": {
        "default_payment_terms": "NET_30",
        "default_credit_limit_cents": 500000,
        "approval_required": True,
    },
    "settings_driver": {
        "background_check_required": True,
        "document_expiry_alert_days": 30,
    },
    "settings_customer": {
        "portal_enabled": True,
        "booking_self_service": True,
        "tracking_notifications": True,
    },
    "settings_finance": {
        "invoice_number_prefix": "INV",
        "receipt_number_prefix": "RCP",
        "default_tax_percent": 13.0,
    },
    "settings_documents": {
        "max_file_size_mb": 25,
        "allowed_types": ["pdf", "jpg", "png", "jpeg"],
        "retention_days": 2555,
    },
    "settings_claims": {
        "investigation_sla_hours": 72,
        "max_compensation_cents": 500000,
    },
    "settings_automation": {
        "queue_retry_max": 3,
        "dispatch_retry_seconds": 60,
    },
    "settings_feature_flags": {
        "beta_live_map": True,
        "beta_order_360": True,
        "experimental_ai_summary": True,
    },
    "vehicle_types": [
        {"id": "sedan", "label": "Sedan", "capacity_kg": 50, "booking_enabled": True, "retail_enabled": True, "merchant_enabled": True, "sort_order": 1},
        {"id": "suv", "label": "SUV", "capacity_kg": 80, "booking_enabled": True, "retail_enabled": True, "merchant_enabled": True, "sort_order": 2},
        {"id": "pickup", "label": "Pickup", "capacity_kg": 500, "booking_enabled": True, "retail_enabled": True, "merchant_enabled": True, "sort_order": 3},
        {"id": "cargo_van", "label": "Cargo Van", "capacity_kg": 900, "booking_enabled": True, "retail_enabled": True, "merchant_enabled": True, "sort_order": 4},
        {"id": "sprinter_van", "label": "Sprinter Van", "capacity_kg": 1200, "booking_enabled": True, "retail_enabled": True, "merchant_enabled": True, "sort_order": 5},
        {"id": "box_truck", "label": "Box Truck", "capacity_kg": 3000, "booking_enabled": True, "retail_enabled": False, "merchant_enabled": True, "sort_order": 6},
    ],
    "service_areas": [{"city": "Toronto", "region": "GTA", "active": True}],
    "settings_delivery_zones": [],
    "package_types": ["parcel", "envelope", "pallet", "fragile"],
    "notification_templates": [],
    "integrations": [],
}


def _clerk_linked(clerk_user_id: str | None) -> bool:
    if not clerk_user_id:
        return False
    return not clerk_user_id.startswith("pending")


def _latest_invitations(db: Session, user_type: str) -> dict[str, UserInvitation]:
    rows = (
        db.query(UserInvitation)
        .filter(UserInvitation.user_type == user_type)
        .order_by(UserInvitation.created_at.desc())
        .all()
    )
    out: dict[str, UserInvitation] = {}
    for row in rows:
        key = row.email.lower().strip()
        if key not in out:
            out[key] = row
    return out


def _invite_status(inv: UserInvitation | None, clerk_user_id: str | None) -> str:
    if inv and inv.revoked_at:
        return "revoked"
    if _clerk_linked(clerk_user_id):
        return "accepted"
    if inv:
        if inv.status == "accepted":
            return "accepted"
        action = (inv.invitation_metadata or {}).get("clerk_action", "")
        if action in ("failed", "error"):
            return "invite_failed"
        return "invite_pending"
    if clerk_user_id and clerk_user_id.startswith("pending"):
        return "invite_pending"
    return "not_invited"


def _identity_status(clerk_user_id: str | None, invite_status: str) -> str:
    if _clerk_linked(clerk_user_id):
        return "registered"
    if invite_status in ("invite_pending", "accepted"):
        return "invite_pending"
    if clerk_user_id and clerk_user_id.startswith("pending"):
        return "invite_pending"
    return "not_registered"


def _status_label(access_status: str, invite_status: str, identity_status: str) -> str:
    access = {
        "authorized": "Authorized",
        "pending_review": "Pending review",
        "suspended": "Suspended",
        "inactive": "Inactive",
        "not_authorized": "Not authorized",
        "merchant_inactive": "Merchant inactive",
    }.get(access_status, access_status.replace("_", " ").title())
    invite = {
        "not_invited": "Not invited",
        "invite_pending": "Invite pending",
        "accepted": "Invite accepted",
        "revoked": "Invite revoked",
        "invite_failed": "Invite failed",
    }.get(invite_status, invite_status.replace("_", " ").title())
    if identity_status == "registered":
        identity = "Clerk registered"
    elif identity_status == "invite_pending":
        identity = "Clerk pending"
    else:
        identity = "No Clerk account"
    return f"{access} · {invite} · {identity}"


def _facet_counts(items: list[PlatformUserItem]) -> PlatformUsersFacets:
    access: dict[str, int] = {}
    invite: dict[str, int] = {}
    identity: dict[str, int] = {}
    account: dict[str, int] = {}
    clerk: dict[str, int] = {}
    for item in items:
        access[item.access_status] = access.get(item.access_status, 0) + 1
        invite[item.invite_status] = invite.get(item.invite_status, 0) + 1
        identity[item.identity_status] = identity.get(item.identity_status, 0) + 1
        key = (item.status or "unknown").lower()
        account[key] = account.get(key, 0) + 1
        if item.clerk_status:
            clerk[item.clerk_status] = clerk.get(item.clerk_status, 0) + 1
    return PlatformUsersFacets(
        access_status=access,
        invite_status=invite,
        identity_status=identity,
        account_status=account,
        clerk_status=clerk,
    )


def _apply_user_filters(
    items: list[PlatformUserItem],
    *,
    search: str | None,
    access_status: str | None,
    invite_status: str | None,
    identity_status: str | None,
    account_status: str | None,
) -> list[PlatformUserItem]:
    def matches(item: PlatformUserItem) -> bool:
        if search:
            q = search.lower().strip()
            hay = f"{item.email} {item.name or ''} {item.organization or ''}".lower()
            if q not in hay:
                return False
        if access_status and item.access_status != access_status:
            return False
        if invite_status and item.invite_status != invite_status:
            return False
        if identity_status and item.identity_status != identity_status:
            return False
        if account_status and (item.status or "").lower() != account_status.lower():
            return False
        return True

    return [i for i in items if matches(i)]


def _enrich_with_clerk(item: PlatformUserItem, snap: ClerkUserSnapshot | None) -> PlatformUserItem:
    if not snap:
        return item
    invite = "accepted" if snap.clerk_user_id else item.invite_status
    identity = "registered"
    access = item.access_status
    if snap.banned:
        access = "suspended"
    name = item.name
    if not name and (snap.first_name or snap.last_name):
        name = " ".join(p for p in (snap.first_name, snap.last_name) if p)
    label = _status_label(access, invite, identity)
    if snap.clerk_status == "banned":
        label = f"{label} · Banned in Clerk"
    elif not snap.password_set and item.provisioned:
        label = f"{label} · Password not set"
    return item.model_copy(
        update={
            "clerk_user_id": snap.clerk_user_id,
            "clerk_linked": True,
            "clerk_status": snap.clerk_status,
            "clerk_email_verified": snap.email_verified,
            "clerk_password_set": snap.password_set,
            "clerk_last_sign_in_at": snap.last_sign_in_at,
            "invite_status": invite,
            "identity_status": identity,
            "access_status": access,
            "status_label": label,
            "name": name,
            "created_at": snap.created_at or item.created_at,
        }
    )


def _merge_clerk_directory(
    items: list[PlatformUserItem],
    settings: Settings,
    user_type: str,
    *,
    limit: int,
    search: str | None,
) -> tuple[list[PlatformUserItem], bool, int]:
    try:
        snaps = fetch_clerk_snapshots(settings, user_type, limit=limit, query=search)
    except Exception:
        logger = __import__("logging").getLogger(__name__)
        logger.warning("clerk_directory_sync_failed", exc_info=True)
        return items, False, 0
    if not snaps:
        return items, False, 0

    by_email = {i.email.lower(): i for i in items}
    merged: list[PlatformUserItem] = []
    for item in items:
        merged.append(_enrich_with_clerk(item, snaps.get(item.email.lower())))

    for email, snap in snaps.items():
        if email in by_email:
            continue
        access = "not_authorized"
        invite = "accepted"
        identity = "registered"
        name = " ".join(p for p in (snap.first_name, snap.last_name) if p) or email.split("@")[0]
        merged.append(
            PlatformUserItem(
                id=f"clerk:{snap.clerk_user_id}",
                user_type=user_type,
                email=email,
                name=name,
                role=user_type if user_type != "staff" else None,
                status=None,
                access_status=access,
                invite_status=invite,
                identity_status=identity,
                status_label=_status_label(access, invite, identity),
                clerk_linked=True,
                clerk_user_id=snap.clerk_user_id,
                provisioned=False,
                clerk_status=snap.clerk_status,
                clerk_email_verified=snap.email_verified,
                clerk_password_set=snap.password_set,
                clerk_last_sign_in_at=snap.last_sign_in_at,
                created_at=snap.created_at or datetime.now(UTC),
            )
        )
    return merged, True, len(snaps)


class AdminSettingsService:
    def __init__(self) -> None:
        self._invitations = InvitationService()

    def list_staff(self, db: Session, *, active_only: bool = True) -> list[AdminUser]:
        q = db.query(AdminUser)
        if active_only:
            q = q.filter(AdminUser.is_active.is_(True))
        return q.order_by(AdminUser.email).all()

    def list_platform_users(
        self,
        db: Session,
        settings: Settings,
        user_type: str,
        *,
        limit: int = 500,
        search: str | None = None,
        access_status: str | None = None,
        invite_status: str | None = None,
        identity_status: str | None = None,
        account_status: str | None = None,
        clerk_status: str | None = None,
    ) -> PlatformUsersResponse:
        invitations = _latest_invitations(db, "admin" if user_type == "staff" else user_type)
        items: list[PlatformUserItem] = []

        if user_type == "staff":
            for u in self.list_staff(db, active_only=False)[:limit]:
                inv = invitations.get(u.email.lower())
                invite = _invite_status(inv, u.clerk_user_id)
                identity = _identity_status(u.clerk_user_id, invite)
                access = "authorized" if u.is_active else "inactive"
                items.append(
                    PlatformUserItem(
                        id=u.id,
                        user_type="staff",
                        email=u.email,
                        name=u.name,
                        role=u.role,
                        status="active" if u.is_active else "inactive",
                        access_status=access,
                        invite_status=invite,
                        identity_status=identity,
                        status_label=_status_label(access, invite, identity),
                        clerk_linked=_clerk_linked(u.clerk_user_id),
                        clerk_user_id=u.clerk_user_id if _clerk_linked(u.clerk_user_id) else None,
                        created_at=u.created_at,
                    )
                )
        elif user_type == "driver":
            for d in db.query(Driver).order_by(Driver.created_at.desc()).limit(limit).all():
                inv = invitations.get(d.email.lower())
                invite = _invite_status(inv, d.clerk_user_id)
                identity = _identity_status(d.clerk_user_id, invite)
                if d.status == DriverStatus.APPROVED.value:
                    access = "authorized"
                elif d.status == DriverStatus.PENDING.value:
                    access = "pending_review"
                elif d.status == DriverStatus.SUSPENDED.value:
                    access = "suspended"
                else:
                    access = "not_authorized"
                items.append(
                    PlatformUserItem(
                        id=d.id,
                        user_type="driver",
                        email=d.email,
                        name=d.full_name,
                        role="driver",
                        status=d.status,
                        access_status=access,
                        invite_status=invite,
                        identity_status=identity,
                        status_label=_status_label(access, invite, identity),
                        clerk_linked=_clerk_linked(d.clerk_user_id),
                        clerk_user_id=d.clerk_user_id if _clerk_linked(d.clerk_user_id) else None,
                        detail_href=f"/drivers/{d.id}",
                        created_at=d.created_at,
                    )
                )
        elif user_type == "customer":
            for c in db.query(Customer).order_by(Customer.created_at.desc()).limit(limit).all():
                inv = invitations.get(c.email.lower())
                invite = _invite_status(inv, c.clerk_user_id)
                identity = _identity_status(c.clerk_user_id, invite)
                access = "authorized"
                items.append(
                    PlatformUserItem(
                        id=c.id,
                        user_type="customer",
                        email=c.email,
                        name=c.customer_reference or c.email.split("@")[0],
                        role="customer",
                        status="active",
                        access_status=access,
                        invite_status=invite if invite != "not_invited" else "accepted",
                        identity_status=identity,
                        status_label=_status_label(access, invite if invite != "not_invited" else "accepted", identity),
                        clerk_linked=_clerk_linked(c.clerk_user_id),
                        clerk_user_id=c.clerk_user_id if _clerk_linked(c.clerk_user_id) else None,
                        created_at=c.created_at,
                    )
                )
        elif user_type == "merchant":
            rows = (
                db.query(MerchantUser, Merchant)
                .join(Merchant, Merchant.id == MerchantUser.merchant_id)
                .order_by(MerchantUser.created_at.desc())
                .limit(limit)
                .all()
            )
            for mu, m in rows:
                inv = invitations.get(mu.email.lower())
                invite = _invite_status(inv, mu.clerk_user_id)
                identity = _identity_status(mu.clerk_user_id, invite)
                if not mu.is_active:
                    access = "inactive"
                elif m.status != MerchantStatus.ACTIVE.value:
                    access = "merchant_inactive"
                else:
                    access = "authorized"
                acct = "active" if mu.is_active else "inactive"
                items.append(
                    PlatformUserItem(
                        id=mu.id,
                        user_type="merchant",
                        email=mu.email,
                        name=mu.email.split("@")[0],
                        role=mu.role,
                        status=acct,
                        organization=m.company_name,
                        access_status=access,
                        invite_status=invite,
                        identity_status=identity,
                        status_label=_status_label(access, invite, identity),
                        clerk_linked=_clerk_linked(mu.clerk_user_id),
                        clerk_user_id=mu.clerk_user_id if _clerk_linked(mu.clerk_user_id) else None,
                        detail_href=f"/merchants/{m.id}",
                        created_at=mu.created_at,
                    )
                )
        else:
            raise ValueError("invalid_user_type")

        items, clerk_synced, clerk_total = _merge_clerk_directory(
            items, settings, user_type, limit=limit, search=search
        )

        facets = _facet_counts(items)

        def matches_clerk(item: PlatformUserItem) -> bool:
            return not clerk_status or item.clerk_status == clerk_status

        filtered = [
            i
            for i in _apply_user_filters(
                items,
                search=search,
                access_status=access_status,
                invite_status=invite_status,
                identity_status=identity_status,
                account_status=account_status,
            )
            if matches_clerk(i)
        ]
        return PlatformUsersResponse(
            items=filtered,
            total=len(filtered),
            facets=facets,
            clerk_synced=clerk_synced,
            clerk_total=clerk_total if clerk_synced else None,
        )

    def invite_staff(
        self,
        db: Session,
        ctx: AdminContext,
        settings: Settings,
        *,
        email: str,
        role: str,
        name: str | None = None,
    ):
        if not is_clerk_secret_configured(settings, "admin"):
            raise ValueError("clerk_not_configured")
        return self._invitations.invite_admin_staff(db, ctx, settings, email=email, role=role, name=name)

    def update_staff_role(
        self,
        db: Session,
        ctx: AdminContext,
        user_id: str,
        role: str,
        *,
        reason: str | None = None,
    ) -> AdminUser:
        user = db.query(AdminUser).filter(AdminUser.id == user_id).first()
        if not user:
            raise LookupError("staff_not_found")
        old_role = user.role
        user.role = role
        log_admin_audit(
            db,
            ctx,
            action="settings.staff.role",
            resource_type="admin_user",
            resource_id=user.id,
            payload={"old": old_role, "new": role, "reason": reason},
        )
        db.commit()
        db.refresh(user)
        return user

    def authorize_platform_user(
        self,
        db: Session,
        ctx: AdminContext,
        settings: Settings,
        user_type: str,
        *,
        platform_user_id: str | None = None,
        clerk_user_id: str | None = None,
        email: str | None = None,
        name: str | None = None,
        reason: str | None = None,
    ) -> PlatformUserAuthorizeResponse:
        from porterchain_api.admin_engine.platform_user_authorize import authorize_platform_user as _authorize

        return _authorize(
            db,
            ctx,
            settings,
            user_type,
            platform_user_id=platform_user_id,
            clerk_user_id=clerk_user_id,
            email=email,
            name=name,
            reason=reason,
        )

    def get_config(self, db: Session, key: str) -> SystemConfig | None:
        return db.query(SystemConfig).filter(SystemConfig.key == key).first()

    def get_config_value(self, db: Session, key: str) -> Any:
        rec = self.get_config(db, key)
        if rec and rec.value is not None:
            return rec.value
        return DEFAULTS.get(key, {})

    def set_config(
        self,
        db: Session,
        ctx: AdminContext,
        key: str,
        value: Any,
        *,
        reason: str | None = None,
    ) -> SystemConfig:
        record = self.get_config(db, key)
        old_value = record.value if record else None
        if record:
            record.value = value
        else:
            record = SystemConfig(key=key, value=value)
            db.add(record)
        log_admin_audit(
            db,
            ctx,
            action="settings.config.update",
            resource_type="system_config",
            resource_id=key,
            payload={"old": old_value, "new": value, "reason": reason},
        )
        db.commit()
        db.refresh(record)
        return record

    def default_config(self, db: Session) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for logical, key in CONFIG_KEYS.items():
            result[logical] = self.get_config_value(db, key)
        return result

    def module_config_links(self, db: Session) -> dict[str, Any]:
        """Read-only pointers to module-owned SystemConfig keys."""
        keys = [
            "support_sla",
            "support_automation",
            "pricing_tax",
            "pricing_fuel",
            "pricing_rate_card",
            "reports_center_saved",
            "reports_center_scheduled",
        ]
        out: dict[str, Any] = {}
        for k in keys:
            rec = self.get_config(db, k)
            if rec:
                out[k] = rec.value
        return out

    def vehicles_overview(self, db: Session) -> dict[str, Any]:
        """Fleet inventory counts keyed by vehicle class — Porterchain mirror, not Fleetbase."""
        fleet_total = (
            db.query(func.count(Vehicle.id)).filter(Vehicle.is_active.is_(True)).scalar() or 0
        )
        fleet_assigned = (
            db.query(func.count(Vehicle.id))
            .filter(Vehicle.is_active.is_(True), Vehicle.driver_id.isnot(None))
            .scalar()
            or 0
        )
        by_class: list[dict[str, Any]] = []
        rows = (
            db.query(Vehicle.vehicle_class, func.count(Vehicle.id))
            .filter(Vehicle.is_active.is_(True))
            .group_by(Vehicle.vehicle_class)
            .all()
        )
        assigned_rows = {
            vc: cnt
            for vc, cnt in db.query(Vehicle.vehicle_class, func.count(Vehicle.id))
            .filter(Vehicle.is_active.is_(True), Vehicle.driver_id.isnot(None))
            .group_by(Vehicle.vehicle_class)
            .all()
        }
        for vehicle_class, fleet_count in rows:
            by_class.append(
                {
                    "vehicle_class": vehicle_class,
                    "fleet_count": int(fleet_count),
                    "assigned_count": int(assigned_rows.get(vehicle_class, 0)),
                }
            )
        booking = self.get_config_value(db, "settings_booking")
        default_class = (
            booking.get("default_vehicle_class", "sedan")
            if isinstance(booking, dict)
            else "sedan"
        )
        return {
            "fleet_total": int(fleet_total),
            "fleet_assigned": int(fleet_assigned),
            "fleet_available": int(fleet_total - fleet_assigned),
            "by_class": sorted(by_class, key=lambda r: r["vehicle_class"]),
            "default_vehicle_class": default_class,
        }

    def integration_health(self, db: Session, settings: Settings) -> dict[str, Any]:
        ready = readiness(db, settings)
        platform = PlatformSettings()
        checks = ready.get("checks", {})
        return {
            "api": ready.get("status", "unknown"),
            "database": checks.get("database", "unknown"),
            "redis": checks.get("redis", "unknown"),
            "queue": checks.get("redis", "unknown"),
            "stripe": {
                "status": checks.get("stripe", "unknown"),
                "mock_mode": settings.stripe_mock,
                "configured": bool(settings.stripe_secret),
            },
            "fleetbase": {
                "status": checks.get("fleetbase", "unknown"),
                "bridge_enabled": settings.fleetbase_dispatch_bridge,
                "configured": bool(settings.fleetbase_api_key),
                "api_url": settings.fleetbase_api_url,
            },
            "google_maps": {
                "status": "configured" if platform.google_maps_api_key else "unconfigured",
                "routing_engine": platform.routing_engine,
            },
            "firebase": {
                "status": "configured" if platform.firebase_project_id else "unconfigured",
                "project_id": platform.firebase_project_id or None,
            },
            "clerk": {
                "status": "configured" if is_clerk_configured(settings) else "dev_bypass"
                if settings.clerk_dev_bypass
                else "unconfigured",
            },
            "storage": {"status": "local", "note": "File storage via API deployment volume"},
            "email": {
                "status": "configured" if platform.smtp_host else "unconfigured",
                "from": platform.smtp_from or None,
            },
            "sms": {
                "status": "log_only",
                "note": "SMS provider not configured — Clerk handles phone verification",
            },
            "push": {
                "status": "configured" if platform.firebase_project_id else "unconfigured",
                "project_id": platform.firebase_project_id or None,
            },
        }

    def dashboard(self, db: Session, settings: Settings) -> dict[str, Any]:
        health = self.integration_health(db, settings)
        overall = "healthy"
        if health["database"] != "ok" or health["redis"] not in ("ok", "unavailable"):
            overall = "degraded"
        return {
            "system_status": overall,
            "version": PORTERCHAIN_VERSION,
            "environment": settings.app_env,
            "health": health,
            "recent_changes": self.recent_audit(db, limit=10),
        }

    def center(self, db: Session, settings: Settings) -> dict[str, Any]:
        return {
            "dashboard": self.dashboard(db, settings),
            "sections": SETTINGS_SECTIONS,
            "config": self.default_config(db),
            "module_config": self.module_config_links(db),
            "permissions": self.permissions_matrix(),
            "roles": [r.value for r in EnterpriseRole],
            "validation": self.validate(settings, db),
        }

    def permissions_matrix(self) -> dict[str, list[str]]:
        from porterchain_api.auth.enterprise_rbac import enterprise_permissions_matrix

        return enterprise_permissions_matrix()

    def recent_audit(self, db: Session, *, limit: int = 50) -> list[dict[str, Any]]:
        logs = (
            db.query(AdminAuditLog)
            .filter(AdminAuditLog.action.like("settings.%"))
            .order_by(AdminAuditLog.created_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": log.id,
                "action": log.action,
                "actor_user_id": log.actor_user_id,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "payload": log.payload,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
            for log in logs
        ]

    def audit_log(self, db: Session, *, limit: int = 100) -> list[dict[str, Any]]:
        logs = (
            db.query(AdminAuditLog)
            .filter(AdminAuditLog.action.like("settings.%"))
            .order_by(AdminAuditLog.created_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "action": log.action,
                "actor_user_id": log.actor_user_id,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "old_value": (log.payload or {}).get("old"),
                "new_value": (log.payload or {}).get("new"),
                "reason": (log.payload or {}).get("reason"),
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
            for log in logs
        ]

    def search(self, query: str) -> list[dict[str, str]]:
        q = query.lower().strip()
        if not q:
            return []
        hits: list[dict[str, str]] = []
        for section in SETTINGS_SECTIONS:
            if q in section["label"].lower() or q in section["id"]:
                hits.append({"type": "section", "id": section["id"], "label": section["label"]})
        for logical, key in CONFIG_KEYS.items():
            if q in logical or q in key:
                hits.append({"type": "config", "id": logical, "label": logical.replace("_", " ").title()})
        return hits[:20]

    def validate(self, settings: Settings, db: Session) -> dict[str, Any]:
        issues: list[str] = []
        warnings: list[str] = []
        platform = PlatformSettings()

        if settings.app_env != "local":
            if not settings.stripe_secret and not settings.stripe_mock:
                issues.append("Stripe secret key missing in non-local environment")
            if settings.fleetbase_dispatch_bridge and not settings.fleetbase_api_key:
                issues.append("Fleetbase API key required when dispatch bridge is enabled")
            if not platform.google_maps_api_key:
                warnings.append("Google Maps server API key not configured")
            if not platform.firebase_project_id:
                warnings.append("Firebase project not configured for push notifications")

        if not is_clerk_configured(settings) and not settings.clerk_dev_bypass:
            warnings.append("Clerk authentication not fully configured")

        ready = readiness(db, settings)
        if ready.get("status") != "ok":
            issues.append(f"Readiness probe status: {ready.get('status')}")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "checked_at": datetime.now(UTC).isoformat(),
        }

    def export_configuration(self, db: Session) -> dict[str, Any]:
        rows = db.query(SystemConfig).all()
        return {
            "exported_at": datetime.now(UTC).isoformat(),
            "version": PORTERCHAIN_VERSION,
            "config": {r.key: r.value for r in rows},
            "defaults": DEFAULTS,
        }

    def import_configuration(
        self,
        db: Session,
        ctx: AdminContext,
        payload: dict[str, Any],
        *,
        reason: str | None = None,
    ) -> dict[str, int]:
        config = payload.get("config") or payload
        if not isinstance(config, dict):
            raise ValueError("invalid_import")
        imported = 0
        for key, value in config.items():
            if key.startswith("settings_") or key in DEFAULTS:
                self.set_config(db, ctx, key, value, reason=reason or "import")
                imported += 1
        return {"imported": imported}
