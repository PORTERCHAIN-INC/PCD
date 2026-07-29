"""Audit helpers for identity migration (counts only — no PII dumps by default)."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.admin_models import AdminUser, Driver
from porterchain_api.auth.identity_migration.types import SourceExportUser
from porterchain_api.merchant_models import MerchantUser
from porterchain_api.models import Customer


def audit_exports(sources: list[SourceExportUser]) -> dict[str, Any]:
    by_app: dict[str, int] = defaultdict(int)
    verified = 0
    with_meta_hint = 0
    emails: dict[str, set[str]] = defaultdict(set)
    for s in sources:
        by_app[s.source_app] += 1
        if s.email_verified:
            verified += 1
        if s.metadata_role_hint:
            with_meta_hint += 1
        if s.email:
            emails[s.email].add(s.source_app)

    multi_app_emails = sum(1 for apps in emails.values() if len(apps) > 1)
    return {
        "source_count": len(sources),
        "by_app": dict(by_app),
        "email_verified_count": verified,
        "metadata_role_hint_count": with_meta_hint,
        "metadata_role_hint_note": "hints are ignored for elevation",
        "emails_shared_across_apps": multi_app_emails,
    }


def audit_legacy_db(db: Session) -> dict[str, Any]:
    """Count legacy clerk_user_id rows — names/counts only."""

    def _count_with_clerk(model) -> dict[str, int]:
        total = db.query(model).count()
        linked = db.query(model).filter(model.clerk_user_id.isnot(None), model.clerk_user_id != "").count()
        return {"total": total, "with_clerk_user_id": linked}

    return {
        "admin_users": _count_with_clerk(AdminUser),
        "merchant_users": _count_with_clerk(MerchantUser),
        "drivers": _count_with_clerk(Driver),
        "customers": _count_with_clerk(Customer),
        "note": "Phase 7 CLI consolidates Clerk subjects into porterchain_users + identity_links; legacy FKs remain until Phase 8",
    }
