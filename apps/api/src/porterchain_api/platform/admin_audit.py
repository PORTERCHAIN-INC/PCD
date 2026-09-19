"""Admin audit writes owned by admin_engine — platform façade so other engines do not import admin_engine."""

from __future__ import annotations

from porterchain_api.admin_engine.audit import log_admin_audit

__all__ = ["log_admin_audit"]
