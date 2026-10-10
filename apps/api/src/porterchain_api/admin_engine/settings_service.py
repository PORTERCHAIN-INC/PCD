"""Enterprise System Settings Center — Application Service (masterrule §3).

Runtime business configuration is stored in SystemConfig. Secrets and infrastructure
endpoints remain in environment variables — the admin UI exposes status only, never secrets.
Module-specific settings (support SLA, reports) are owned by their modules;
this service surfaces them for read/link without duplicating write paths.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.audit import log_admin_audit
from porterchain_api.admin_engine.pricing_versioning import bump_price_version
from porterchain_api.domain.pricing_version import (
    PRICING_STORAGE_KEYS,
    SUPER_ADMIN_SETTING_KEYS,
    assert_pricing_editor,
)
from porterchain_pricing.delivery_promise import default_delivery_promise, normalize_delivery_promise
from porterchain_api.marketing_site.config import default_marketing_site, normalize_marketing_site
from porterchain_pricing.driver_pay import default_driver_pay_plan, normalize_driver_pay_plan
from porterchain_pricing.price_book import default_price_book, normalize_price_book
from porterchain_api.admin_engine.rbac import AdminContext
from porterchain_api.admin_models import AdminAuditLog, AdminUser, Driver, SystemConfig, Vehicle
from porterchain_api.admin_engine.clerk_directory_service import fetch_clerk_snapshots
from porterchain_api.auth.clerk_client import ClerkUserSnapshot
from porterchain_api.auth.clerk_registry import is_clerk_configured, is_clerk_secret_configured
from porterchain_api.auth.invitation_service import InvitationService
from porterchain_api.config import Settings
from porterchain_api.invitation_models import UserInvitation
from porterchain_api.merchant_engine.lookups import list_directory_seats
from porterchain_api.booking_models import Customer
from porterchain_api.schemas_admin import (
    PlatformUserAuthorizeResponse,
    PlatformUserItem,
    PlatformUsersFacets,
    PlatformUsersResponse,
)
from porterchain_api.domain.admin_states import DriverStatus
from porterchain_api.domain.merchant_states import MerchantStatus
from porterchain_api.platform.health import readiness
from porterchain_shared.config.settings import PlatformSettings


PORTERCHAIN_VERSION = os.environ.get("PORTERCHAIN_VERSION", "3.1.0")

SETTINGS_SECTIONS: list[dict[str, str]] = [
    {"id": "dashboard", "label": "Dashboard", "group": "overview"},
    {"id": "general", "label": "Company", "group": "general"},
    {"id": "users", "label": "Users", "group": "access"},
    {"id": "roles", "label": "Roles & Permissions", "group": "access"},
    {"id": "authentication", "label": "Authentication", "group": "access"},
    {"id": "security", "label": "Security", "group": "access"},
    {"id": "vehicles", "label": "Vehicle Classes", "group": "commercial"},
    {"id": "pricing", "label": "Pricing", "group": "commercial"},
    {"id": "coverage", "label": "Coverage", "group": "commercial"},
    {"id": "booking", "label": "Booking", "group": "commercial"},
    {"id": "finance", "label": "Finance", "group": "commercial"},
    {"id": "documents", "label": "Documents", "group": "commercial"},
    {"id": "claims", "label": "Claims", "group": "commercial"},
    {"id": "merchant", "label": "Merchant", "group": "partners"},
    {"id": "driver", "label": "Driver", "group": "partners"},
    {"id": "customer", "label": "Customer", "group": "partners"},
    {"id": "dispatch", "label": "Dispatch", "group": "connections"},
    {"id": "stripe", "label": "Stripe", "group": "connections"},
    {"id": "google_maps", "label": "Google Maps", "group": "connections"},
    {"id": "firebase", "label": "Firebase", "group": "connections"},
    {"id": "storage", "label": "Storage", "group": "connections"},
    {"id": "channels", "label": "Channels", "group": "connections"},
    {"id": "lead_ingest", "label": "Lead Ingest", "group": "connections"},
    {"id": "automation", "label": "Automation", "group": "platform"},
    {"id": "audit", "label": "Audit", "group": "platform"},
    {"id": "backup", "label": "Backup", "group": "platform"},
]

CONFIG_KEYS = {
    "general": "settings_general",
    "booking": "settings_booking",
    "merchant": "settings_merchant",
    "driver": "settings_driver",
    "customer": "settings_customer",
    "finance": "settings_finance",
    "documents": "settings_documents",
    "claims": "settings_claims",
    "automation": "settings_automation",
    "vehicles": "vehicle_types",
    "pricing": "pricing_gta_rate",
    "pricing_customer": "pricing_customer_distance",
    "pricing_tax": "pricing_tax",
    "pricing_fuel": "pricing_fuel",
    "pricing_rate_card": "pricing_rate_card",
    # Price book (parcel tiers, small/handling rules, retail, dedicated) + driver pay plan.
    "pricing_book": "pricing_book",
    "driver_pay": "driver_pay_plan",
    # Checkout delivery promise (cut-offs, waves, holidays, FSA tiers). Off by default.
    "delivery_promise": "delivery_promise",
    # Website marketing switches (hero A/B flag, calculator limits). A/B off by default.
    "marketing_site": "marketing_site",
    "coverage": "settings_coverage",
    # Legacy storage keys still readable for migration
    "service_areas": "service_areas",
    "delivery_zones": "settings_delivery_zones",
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
    # Branding / auth / security SystemConfig rows were decorative theater —
    # Staff IdP + Clerk + env own those surfaces. Do not reintroduce defaults.
    "settings_booking": {
        "quote_ttl_minutes": 30,
        "booking_draft_ttl_minutes": 1440,
        "default_currency": "cad",
        "default_vehicle_class": "sedan_suv",
        # ASAP / INSTANT promise window used by order SLA (not the same as scheduled_at).
        "instant_delivery_sla_hours": 4,
    },
    "settings_merchant": {
        "default_payment_terms": "NET_30",
        "default_credit_limit_cents": 500000,
        # Untrusted signups (portal walk-ins) wait for an admin.
        "approval_required": True,
        # Verified integration installs (Shopify OAuth) skip that wait. Turn off
        # to force every channel through manual review.
        "auto_activate_trusted_channels": True,
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
        "tax_name": "HST",
        "gst_hst_number": "",
        "etransfer_email": "billing@porterchain.com",
        "etransfer_autodeposit": True,
        "merchant_cycle_invoicing": True,
        "tax_mode": "exclusive",
        "default_tax_province": "ON",
        "collect_qst": False,
        "margin_floor_pct": 25.0,
        "margin_minutes_per_stop": 30,
        "interac_retention_years": 7,
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
        "queue_retry_max": 5,
        "dispatch_retry_seconds": 60,
    },
    "vehicle_types": None,  # filled below from customer_goods so one catalog is the source
    # GTA delivery rate matrix — filled below from porterchain_pricing (one source of defaults)
    "pricing_gta_rate": None,
    "pricing_customer_distance": None,
    "pricing_tax": {"hst_percent": 13.0, "tax_included": False, "exempt_merchant_ids": []},
    "pricing_fuel": {
        "surcharge_percent": 5.0,
        "base_fuel_price_cents": 145,
        "current_fuel_price_cents": 158,
    },
    "pricing_rate_card": {
        "liftgate_cents": 4500,
        "extra_stop_cents": 0,
        "weight_threshold_kg": 50.0,
        "weight_cents_per_kg": 0,
        "driver_payout_mode": "flat",
        "driver_flat_per_delivery_cents": 850,
        "driver_share_pct": 72.0,
        "platform_share_pct": 28.0,
    },
    "settings_coverage": {
        "areas": [{"city": "Toronto", "region": "GTA", "active": True}],
        "zones": [],
    },
    "service_areas": [{"city": "Toronto", "region": "GTA", "active": True}],
    "settings_delivery_zones": [],
}

from porterchain_api.domain.customer_goods import default_customer_pricing, default_vehicle_catalog
from porterchain_pricing.gta_rate import default_gta_rate_config

DEFAULTS["vehicle_types"] = default_vehicle_catalog()
DEFAULTS["pricing_customer_distance"] = default_customer_pricing()
DEFAULTS["pricing_gta_rate"] = default_gta_rate_config().to_dict()
DEFAULTS["pricing_book"] = default_price_book()
DEFAULTS["driver_pay_plan"] = default_driver_pay_plan()
DEFAULTS["delivery_promise"] = default_delivery_promise()
DEFAULTS["marketing_site"] = default_marketing_site()


def _is_pending_subject(subject: str | None) -> bool:
    return bool(subject) and subject.startswith("pending")


def _is_staff_subject(subject: str | None) -> bool:
    return bool(subject) and subject.startswith("staff:")


def _is_legacy_clerk_staff_id(subject: str | None) -> bool:
    """Pre-cutover AdminUser rows still holding a Clerk ``user_…`` id."""
    return bool(subject) and subject.startswith("user_")


def _clerk_linked(clerk_user_id: str | None) -> bool:
    """True only for real Clerk ``user_…`` (or other non-pending, non-staff) ids."""
    if not clerk_user_id:
        return False
    if _is_pending_subject(clerk_user_id) or _is_staff_subject(clerk_user_id):
        return False
    return True


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
    if _is_pending_subject(clerk_user_id):
        return "invite_pending"
    return "not_invited"


def _identity_status(clerk_user_id: str | None, invite_status: str) -> str:
    if _clerk_linked(clerk_user_id):
        return "registered"
    if invite_status in ("invite_pending", "accepted"):
        return "invite_pending"
    if _is_pending_subject(clerk_user_id):
        return "invite_pending"
    return "not_registered"


def _staff_invite_status(subject: str | None) -> str:
    if _is_staff_subject(subject) or _is_legacy_clerk_staff_id(subject):
        return "accepted"
    if _is_pending_subject(subject):
        return "invite_pending"
    return "not_invited"


def _staff_identity_status(subject: str | None) -> str:
    if _is_staff_subject(subject):
        return "registered"
    if _is_legacy_clerk_staff_id(subject):
        # Still provisioned; subject rebinds to staff:{id} on next IdP login/enroll.
        return "registered"
    if _is_pending_subject(subject):
        return "invite_pending"
    return "not_registered"


def _access_label(access_status: str) -> str:
    return {
        "authorized": "Authorized",
        "pending_review": "Pending review",
        "suspended": "Suspended",
        "inactive": "Inactive",
        "not_authorized": "Not authorized",
        "merchant_inactive": "Merchant inactive",
    }.get(access_status, access_status.replace("_", " ").title())


def _invite_label(invite_status: str) -> str:
    return {
        "not_invited": "Not invited",
        "invite_pending": "Invite pending",
        "accepted": "Invite accepted",
        "revoked": "Invite revoked",
        "invite_failed": "Invite failed",
    }.get(invite_status, invite_status.replace("_", " ").title())


def _status_label(access_status: str, invite_status: str, identity_status: str) -> str:
    """Clerk-persona status line (driver / merchant / customer)."""
    if identity_status == "registered":
        identity = "Clerk registered"
    elif identity_status == "invite_pending":
        identity = "Clerk pending"
    else:
        identity = "No Clerk account"
    return f"{_access_label(access_status)} · {_invite_label(invite_status)} · {identity}"


def _staff_status_label(
    access_status: str,
    invite_status: str,
    identity_status: str,
    *,
    subject: str | None = None,
) -> str:
    """Staff IdP status line — never mentions Clerk as the live auth path."""
    invite = {
        "not_invited": "Not enrolled",
        "invite_pending": "Activation pending",
        "accepted": "Enrolled",
        "revoked": "Revoked",
        "invite_failed": "Enroll failed",
    }.get(invite_status, invite_status.replace("_", " ").title())
    if _is_legacy_clerk_staff_id(subject):
        identity = "Legacy id (rebinds on login)"
    elif identity_status == "registered":
        identity = "Staff IdP bound"
    elif identity_status == "invite_pending":
        identity = "Awaiting activation"
    else:
        identity = "Not bound"
    return f"{_access_label(access_status)} · {invite} · {identity}"


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


from porterchain_api.admin_engine.settings_clerk_merge import (  # noqa: E402
    _enrich_with_clerk,
    _mark_not_in_clerk,
    _merge_clerk_directory,
)



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
        limit: int = 5000,
        search: str | None = None,
        access_status: str | None = None,
        invite_status: str | None = None,
        identity_status: str | None = None,
        account_status: str | None = None,
        clerk_status: str | None = None,
    ) -> PlatformUsersResponse:
        items: list[PlatformUserItem] = []

        if user_type == "staff":
            # Staff IdP SoT — AdminUser rows only; never intersect retired Clerk admin app.
            for u in self.list_staff(db, active_only=False)[:limit]:
                invite = _staff_invite_status(u.clerk_user_id)
                identity = _staff_identity_status(u.clerk_user_id)
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
                        status_label=_staff_status_label(
                            access, invite, identity, subject=u.clerk_user_id
                        ),
                        clerk_linked=False,
                        clerk_user_id=None,
                        provisioned=True,
                        created_at=u.created_at,
                    )
                )
            facets = _facet_counts(items)
            filtered = _apply_user_filters(
                items,
                search=search,
                access_status=access_status,
                invite_status=invite_status,
                identity_status=identity_status,
                account_status=account_status,
            )
            return PlatformUsersResponse(
                items=filtered,
                total=len(filtered),
                facets=facets,
                clerk_synced=False,
                clerk_total=None,
            )

        invitations = _latest_invitations(db, user_type)
        if user_type == "driver":
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
                linked = _clerk_linked(c.clerk_user_id)
                identity = "registered" if linked else "not_registered"
                access = "authorized" if linked else "not_authorized"
                invite = "accepted" if linked else "not_invited"
                hold = (c.privacy_status or "").lower() == "deletion_hold"
                items.append(
                    PlatformUserItem(
                        id=c.id,
                        user_type="customer",
                        email=c.email,
                        name=c.customer_reference or c.email.split("@")[0],
                        role="customer",
                        status="deletion_hold" if hold else ("active" if linked else "orphan"),
                        access_status=access,
                        invite_status=invite,
                        identity_status=identity,
                        status_label=(
                            f"DSR hold · {c.privacy_hold_reference}"
                            if hold
                            else _status_label(access, invite, identity)
                        ),
                        clerk_linked=linked,
                        clerk_user_id=c.clerk_user_id if linked else None,
                        detail_href=f"/customers/{c.id}",
                        created_at=c.created_at,
                    )
                )
        elif user_type == "merchant":
            rows = list_directory_seats(db, limit=limit)
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

        # PorterChain DB is the directory SoT. Clerk enriches identity when available.
        # Merchant also injects Clerk-only orphans (no seat yet).
        items, clerk_synced, clerk_total = _merge_clerk_directory(
            items,
            settings,
            user_type,
            limit=limit,
            search=search,
            include_unprovisioned=user_type == "merchant",
            keep_unlinked=True,
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
        from porterchain_api.auth.authz_sync import sync_authz_after_persona_mutation
        from porterchain_api.auth.staff_session import revoke_all_for_user

        sync_authz_after_persona_mutation(db, user.clerk_user_id)
        # Force re-auth after privilege change.
        revoke_all_for_user(user.id)
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
            value = rec.value
        else:
            value = DEFAULTS.get(key, {})
        if key == "pricing_gta_rate" and isinstance(value, dict):
            return self._normalize_pricing_gta(value)
        if key == "pricing_customer_distance" and isinstance(value, dict):
            from porterchain_api.domain.customer_goods import normalize_customer_pricing

            return normalize_customer_pricing(value)
        if key == "pricing_rate_card" and isinstance(value, dict):
            return self._normalize_pricing_rate_card(value)
        if key == "pricing_book":
            try:
                return normalize_price_book(value)
            except ValueError:
                return value
        if key == "driver_pay_plan":
            try:
                return normalize_driver_pay_plan(value)
            except ValueError:
                return value
        if key == "delivery_promise":
            try:
                return normalize_delivery_promise(value)
            except ValueError:
                return value
        if key == "marketing_site":
            try:
                return normalize_marketing_site(value)
            except ValueError:
                return value
        if key == "settings_coverage":
            return self._coverage_value(db, value)
        return value

    @staticmethod
    def _normalize_pricing_gta(raw: dict[str, Any]) -> dict[str, Any]:
        try:
            from porterchain_pricing.gta_rate import gta_rate_config_from_dict

            return gta_rate_config_from_dict(raw).to_dict()
        except Exception:
            return raw

    @staticmethod
    def _normalize_pricing_rate_card(
        raw: dict[str, Any],
        *,
        existing: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Merge commercial knobs onto the stored card so driver payout is not wiped."""
        from porterchain_pricing.rate_card import default_rate_card, rate_card_from_dict

        base = default_rate_card()
        if existing:
            base = rate_card_from_dict(existing, base=base)
        return rate_card_from_dict(raw, base=base).to_dict()

    def _coverage_value(self, db: Session, value: Any) -> dict[str, Any]:
        if isinstance(value, dict) and ("areas" in value or "zones" in value):
            return {
                "areas": value.get("areas")
                if isinstance(value.get("areas"), list)
                else DEFAULTS["settings_coverage"]["areas"],
                "zones": value.get("zones") if isinstance(value.get("zones"), list) else [],
            }
        areas = self.get_config(db, "service_areas")
        zones = self.get_config(db, "settings_delivery_zones")
        return {
            "areas": areas.value
            if areas and isinstance(areas.value, list)
            else DEFAULTS["settings_coverage"]["areas"],
            "zones": zones.value if zones and isinstance(zones.value, list) else [],
        }

    def enabled_retail_vehicle_ids(self, db: Session) -> set[str]:
        catalog = self.get_config_value(db, "vehicle_types")
        if not isinstance(catalog, list):
            return set()
        out: set[str] = set()
        for row in catalog:
            if not isinstance(row, dict):
                continue
            from porterchain_api.domain.customer_goods import canonical_vehicle_id

            vid = canonical_vehicle_id(str(row.get("id") or "").strip())
            if not vid:
                continue
            if row.get("booking_enabled") is False:
                continue
            if row.get("retail_enabled") is False:
                continue
            out.add(vid)
        return out

    def set_config(
        self,
        db: Session,
        ctx: AdminContext,
        key: str,
        value: Any,
        *,
        reason: str | None = None,
    ) -> SystemConfig:
        pricing_key = key in PRICING_STORAGE_KEYS
        card_pruned = False
        if pricing_key or key in SUPER_ADMIN_SETTING_KEYS:
            # Covers PUT, audit restore and config import — all write through here.
            assert_pricing_editor(ctx)
        record = self.get_config(db, key)
        if key == "pricing_book":
            value = normalize_price_book(value)
        if key == "driver_pay_plan":
            value = normalize_driver_pay_plan(value)
        if key == "delivery_promise":
            value = normalize_delivery_promise(value)
        if key == "marketing_site":
            value = normalize_marketing_site(value)
        if key == "pricing_gta_rate" and isinstance(value, dict):
            value = self._normalize_pricing_gta(value)
        if key == "pricing_customer_distance" and isinstance(value, dict):
            from porterchain_api.domain.customer_goods import normalize_customer_pricing

            value = normalize_customer_pricing(value)
        if key == "vehicle_types" and isinstance(value, list):
            from porterchain_api.domain.customer_goods import canonical_vehicle_id

            kept = {
                canonical_vehicle_id(str(row.get("id") or ""))
                for row in value
                if isinstance(row, dict) and str(row.get("id") or "").strip()
            }
            kept.discard("")
            card_rec = self.get_config(db, "pricing_customer_distance")
            if card_rec and isinstance(card_rec.value, dict) and isinstance(card_rec.value.get("vehicles"), dict):
                vehicles = card_rec.value["vehicles"]
                next_vehicles = {
                    vid: rate for vid, rate in vehicles.items() if canonical_vehicle_id(str(vid)) in kept
                }
                if next_vehicles != vehicles:
                    card_rec.value = {**card_rec.value, "vehicles": next_vehicles}
                    card_pruned = True
        if key == "pricing_rate_card" and isinstance(value, dict):
            existing = record.value if record and isinstance(record.value, dict) else None
            value = self._normalize_pricing_rate_card(value, existing=existing)
        if isinstance(value, float) and value != value:  # NaN
            raise ValueError("invalid_config_value")
        if isinstance(value, dict):
            for v in value.values():
                if isinstance(v, float) and v != v:
                    raise ValueError("invalid_config_value")
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
        if (pricing_key and old_value != value) or card_pruned:
            bump_price_version(db, ctx, source=f"settings:{key}", reason=reason)
        db.commit()
        if key == "settings_booking":
            from porterchain_api.booking_engine.order_sla import refresh_open_sla_deadlines

            refresh_open_sla_deadlines(db)
            db.commit()
        db.refresh(record)
        return record

    def default_config(self, db: Session) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for logical, key in CONFIG_KEYS.items():
            if logical in ("service_areas", "delivery_zones"):
                continue
            result[logical] = self.get_config_value(db, key)
        return result

    def module_config_links(self, db: Session) -> dict[str, Any]:
        """Read-only pointers to module-owned SystemConfig keys."""
        keys = [
            "support_sla",
            "support_automation",
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
        """Fleet inventory counts keyed by vehicle class — from PorterChain vehicles."""
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
            booking.get("default_vehicle_class", "sedan_suv")
            if isinstance(booking, dict)
            else "sedan_suv"
        )
        return {
            "fleet_total": int(fleet_total),
            "fleet_assigned": int(fleet_assigned),
            "fleet_available": int(fleet_total - fleet_assigned),
            "by_class": sorted(by_class, key=lambda r: r["vehicle_class"]),
            "default_vehicle_class": default_class,
        }

    def integration_health(
        self,
        db: Session,
        settings: Settings,
        *,
        ready: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        from porterchain_api.admin_engine.integration_health import build_integration_health
        from porterchain_api.intelligence_engine import nim_client
        from porterchain_shared.config.settings import PlatformSettings

        platform = PlatformSettings()
        return build_integration_health(
            db,
            settings,
            ready=ready,
            nvidia_nim_configured=nim_client.nim_configured(),
            nvidia_model=getattr(platform, "nvidia_model", None),
        )

    def dashboard(self, db: Session, settings: Settings) -> dict[str, Any]:
        from porterchain_api.platform.health_status import component_status_value

        health = self.integration_health(db, settings)
        db_status = component_status_value(health.get("database"))
        redis_status = component_status_value(health.get("redis"))
        overall = "healthy"
        # Redis unavailable is warning (local-ok); only critical redis/db degrade overall.
        if db_status != "healthy" or redis_status == "critical":
            overall = "degraded"
        return {
            "system_status": overall,
            "version": PORTERCHAIN_VERSION,
            "environment": settings.app_env,
            "project_mode": settings.runtime_posture,
            "health": health,
            "recent_changes": self.recent_audit(db, limit=10),
        }

    def center(self, db: Session, settings: Settings) -> dict[str, Any]:
        from porterchain_api.admin_engine.rbac import permissions_catalog
        from porterchain_api.admin_engine.settings_bindings import bindings_payload

        catalog = permissions_catalog()
        return {
            "dashboard": self.dashboard(db, settings),
            "sections": SETTINGS_SECTIONS,
            "config": self.default_config(db),
            "module_config": self.module_config_links(db),
            "bindings": bindings_payload(),
            "env_runtime": {
                "quote_ttl_minutes": settings.quote_ttl_minutes,
                "booking_draft_ttl_minutes": settings.booking_draft_ttl_minutes,
            },
            "permissions": {m["module"]: m["roles"] for m in catalog["modules"]},
            "roles": catalog["roles"],
            "role_catalog": catalog,
            "authz": {
                "engine": "spicedb",
                "docs": "docs/architecture/auth-clerk-spicedb.md",
                "schema": "apps/api/src/porterchain_api/authz/schema.zed",
            },
            "validation": self.validate(settings, db),
        }

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
                "id": log.id,
                "action": log.action,
                "actor_user_id": log.actor_user_id,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "old_value": (log.payload or {}).get("old"),
                "new_value": (log.payload or {}).get("new"),
                "reason": (log.payload or {}).get("reason"),
                "created_at": log.created_at.isoformat() if log.created_at else None,
                "restorable": bool(
                    log.action == "settings.config.update"
                    and log.resource_id
                    and "old" in (log.payload or {})
                ),
            }
            for log in logs
        ]

    def restore_config_from_audit(
        self,
        db: Session,
        ctx: AdminContext,
        audit_id: str,
        *,
        reason: str | None = None,
    ) -> SystemConfig:
        """Restore SystemConfig to the ``old`` value captured on a settings.config.update audit row."""
        log = db.query(AdminAuditLog).filter(AdminAuditLog.id == audit_id).first()
        if not log:
            raise LookupError("audit_not_found")
        if log.action != "settings.config.update":
            raise ValueError("audit_not_restorable")
        key = log.resource_id
        if not key:
            raise ValueError("audit_missing_config_key")
        payload = log.payload or {}
        if "old" not in payload:
            raise ValueError("audit_missing_old_value")
        restore_reason = (reason or "").strip() or f"Rollback from audit {audit_id}"
        return self.set_config(db, ctx, key, payload.get("old"), reason=restore_reason)

    def search(self, query: str) -> list[dict[str, str]]:
        from porterchain_api.admin_engine.settings_bindings import FIELD_SEARCH, SECTION_ALIASES

        q = query.lower().strip()
        if not q:
            return []
        hits: list[dict[str, str]] = []
        seen: set[str] = set()
        for section in SETTINGS_SECTIONS:
            if q in section["label"].lower() or q in section["id"]:
                hits.append({"type": "section", "id": section["id"], "label": section["label"]})
                seen.add(section["id"])
        for logical in CONFIG_KEYS:
            if q in logical and logical not in seen:
                hits.append(
                    {
                        "type": "config",
                        "id": logical if logical != "coverage" else "coverage",
                        "label": logical.replace("_", " ").title(),
                    }
                )
                seen.add(logical)
        for field in FIELD_SEARCH:
            if q in field["q"] or any(part in field["q"] for part in q.split() if len(part) > 2):
                sid = field["section"]
                if sid not in seen:
                    hits.append({"type": "field", "id": sid, "label": field["label"]})
                    seen.add(sid)
        alias_target = SECTION_ALIASES.get(q)
        if alias_target and alias_target not in seen:
            hits.append({"type": "alias", "id": alias_target, "label": f"→ {alias_target}"})
        return hits[:20]

    def validate(self, settings: Settings, db: Session) -> dict[str, Any]:
        issues: list[str] = []
        warnings: list[str] = []
        platform = PlatformSettings()

        if settings.app_env != "local":
            if not settings.stripe_secret and not settings.stripe_mock:
                issues.append("Stripe secret key missing in non-local environment")
            if not platform.google_maps_api_key:
                warnings.append("Google Maps Places key not configured (tiles/autocomplete)")
            if not platform.firebase_project_id:
                warnings.append("Firebase project not configured for push notifications")

        if not is_clerk_configured(settings) and not settings.clerk_dev_bypass:
            warnings.append("Clerk authentication not fully configured")

        ready = readiness(db, settings)
        if ready.get("status") != "ok":
            issues.append(f"Readiness probe status: {ready.get('status')}")

        # Commercial integrity
        from porterchain_api.domain.customer_goods import canonical_vehicle_id

        catalog = self.get_config_value(db, "vehicle_types")
        pricing = self.get_config_value(db, "pricing_gta_rate")
        customer_pricing = self.get_config_value(db, "pricing_customer_distance")
        booking = self.get_config_value(db, "settings_booking")
        catalog_ids: set[str] = set()
        customer_vehicles = (
            customer_pricing.get("vehicles") if isinstance(customer_pricing, dict) else None
        )
        if isinstance(catalog, list):
            for row in catalog:
                if isinstance(row, dict) and row.get("id"):
                    catalog_ids.add(canonical_vehicle_id(str(row["id"])))
                    if row.get("booking_enabled") is not False and row.get("retail_enabled") is not False:
                        vid = canonical_vehicle_id(str(row["id"]))
                        if isinstance(customer_vehicles, dict):
                            customer_ids = {
                                canonical_vehicle_id(str(k)) for k in customer_vehicles
                            }
                            if vid not in customer_ids:
                                issues.append(f"Enabled vehicle '{vid}' has no customer distance rate")
        if isinstance(pricing, dict):
            vehicles = pricing.get("vehicles")
            if isinstance(vehicles, dict):
                for vid, rates in vehicles.items():
                    canon = canonical_vehicle_id(str(vid))
                    if catalog_ids and canon not in catalog_ids:
                        warnings.append(f"Pricing row '{vid}' is not in vehicle catalog")
                    if isinstance(rates, dict):
                        for rk, rv in rates.items():
                            try:
                                if float(rv) < 0:
                                    issues.append(f"Negative rate {rk} for vehicle '{vid}'")
                            except (TypeError, ValueError):
                                issues.append(f"Invalid rate {rk} for vehicle '{vid}'")
        if isinstance(booking, dict):
            default_class = booking.get("default_vehicle_class")
            if default_class and catalog_ids and canonical_vehicle_id(str(default_class)) not in catalog_ids:
                issues.append(f"Default vehicle '{default_class}' is not in vehicle catalog")
            sla = booking.get("instant_delivery_sla_hours")
            if sla is not None:
                try:
                    if float(sla) <= 0:
                        issues.append("instant_delivery_sla_hours must be > 0")
                except (TypeError, ValueError):
                    issues.append("instant_delivery_sla_hours is not a number")
            # TTL in SystemConfig does not bind runtime — warn if diverges from env
            ui_ttl = booking.get("quote_ttl_minutes")
            if ui_ttl is not None and int(ui_ttl) != int(settings.quote_ttl_minutes):
                warnings.append(
                    f"Booking quote_ttl_minutes in Settings ({ui_ttl}) differs from env "
                    f"({settings.quote_ttl_minutes}) — runtime uses env"
                )

        wired_ok = len([i for i in issues if "vehicle" in i.lower() or "pricing" in i.lower() or "sla" in i.lower()]) == 0
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "commercial_ok": wired_ok and len(issues) == 0,
            "checked_at": datetime.now(UTC).isoformat(),
        }

    def export_configuration(self, db: Session) -> dict[str, Any]:
        owned = set(CONFIG_KEYS.values()) | set(DEFAULTS.keys())
        rows = db.query(SystemConfig).filter(SystemConfig.key.in_(owned)).all()
        return {
            "exported_at": datetime.now(UTC).isoformat(),
            "version": PORTERCHAIN_VERSION,
            "config": {r.key: r.value for r in rows},
            "defaults": {k: DEFAULTS[k] for k in DEFAULTS if k in owned},
        }

    def import_preview(self, db: Session, payload: dict[str, Any]) -> dict[str, Any]:
        config = payload.get("config") or payload
        if not isinstance(config, dict):
            raise ValueError("invalid_import")
        owned = set(CONFIG_KEYS.values()) | {
            k for k in DEFAULTS if k.startswith("settings_") or k in (
                "vehicle_types",
                "pricing_gta_rate",
                "pricing_customer_distance",
                "pricing_tax",
                "pricing_fuel",
                "pricing_rate_card",
                "settings_coverage",
            )
        }
        added: list[str] = []
        changed: list[str] = []
        blocked: list[str] = []
        for key, value in config.items():
            if key not in owned and not str(key).startswith("settings_"):
                blocked.append(str(key))
                continue
            if key not in owned and str(key).startswith("settings_"):
                # only known settings_* from DEFAULTS
                if key not in DEFAULTS:
                    blocked.append(str(key))
                    continue
            current = self.get_config(db, key)
            if current is None:
                added.append(str(key))
            elif current.value != value:
                changed.append(str(key))
        return {
            "added": added,
            "changed": changed,
            "blocked": blocked,
            "would_write": len(added) + len(changed),
        }

    def import_configuration(
        self,
        db: Session,
        ctx: AdminContext,
        payload: dict[str, Any],
        *,
        reason: str | None = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        preview = self.import_preview(db, payload)
        if dry_run:
            return {"dry_run": True, **preview}
        if not reason or not str(reason).strip():
            raise ValueError("import_reason_required")
        config = payload.get("config") or payload
        if not isinstance(config, dict):
            raise ValueError("invalid_import")
        blocked = set(preview["blocked"])
        allowed = set(CONFIG_KEYS.values()) | {
            k
            for k in DEFAULTS
            if k.startswith("settings_")
            or k
            in (
                "vehicle_types",
                "pricing_gta_rate",
                "pricing_customer_distance",
                "pricing_tax",
                "pricing_fuel",
                "pricing_rate_card",
                "settings_coverage",
            )
        }
        imported = 0
        for key, value in config.items():
            if key in blocked or key not in allowed:
                continue
            self.set_config(db, ctx, key, value, reason=reason)
            imported += 1
        return {"imported": imported, "dry_run": False, **preview}

# Re-exports kept for existing importers (integration).
from porterchain_api.admin_engine.clerk_directory_service import fetch_clerk_snapshots  # noqa: E402, F401
from porterchain_api.auth.clerk_registry import is_clerk_secret_configured  # noqa: E402, F401
from porterchain_api.auth.clerk_client import ClerkUserSnapshot  # noqa: E402, F401
from porterchain_api.admin_engine.settings_clerk_merge import _enrich_with_clerk  # noqa: E402, F401
from porterchain_api.admin_engine.settings_clerk_merge import _mark_not_in_clerk  # noqa: E402, F401
