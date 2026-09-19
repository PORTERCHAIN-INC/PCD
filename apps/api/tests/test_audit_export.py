"""Admin audit export tests (§11.1.7)."""

from __future__ import annotations

from porterchain_api.admin_engine.audit_export_service import AdminAuditExportService


def test_list_logs_empty(db):
    svc = AdminAuditExportService()
    rows = svc.list_logs(db, limit=10)
    assert isinstance(rows, list)


def test_domain_events_empty(db):
    svc = AdminAuditExportService()
    rows = svc.domain_events(db, limit=10)
    assert isinstance(rows, list)


def test_export_bundle_shape(db):
    svc = AdminAuditExportService()
    bundle = svc.export_bundle(db, limit=5)
    assert "exported_at" in bundle
    assert "admin_audit_logs" in bundle
    assert "domain_events" in bundle


def test_export_csv_header(db):
    svc = AdminAuditExportService()
    csv_text = svc.export_csv(db, limit=5)
    assert csv_text.startswith("created_at,action,actor_user_id")
