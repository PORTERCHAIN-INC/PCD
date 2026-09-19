"""admin routes — audit log export (§11.1.7)."""

from fastapi import Response

from porterchain_api.routers.admin._deps import (
    AdminContext,
    Annotated,
    Depends,
    Query,
    Session,
    _audit_export,
    get_admin_context,
    get_db,
    require_module,
    router,
)


@router.get("/audit-logs")
def list_audit_logs(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    resource_type: str | None = None,
    action_prefix: str | None = None,
    limit: int = Query(500, le=2000),
):
    require_module(ctx, "settings")
    return _audit_export.list_logs(
        db, resource_type=resource_type, action_prefix=action_prefix, limit=limit
    )


@router.get("/audit-logs/export")
def export_audit_logs(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    limit: int = Query(1000, le=5000),
):
    require_module(ctx, "settings")
    return _audit_export.export_bundle(db, limit=limit)


@router.get("/audit-logs/export.csv")
def export_audit_logs_csv(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    limit: int = Query(1000, le=5000),
):
    require_module(ctx, "settings")
    csv_text = _audit_export.export_csv(db, limit=limit)
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="porterchain-admin-audit.csv"'},
    )


@router.get("/audit-logs/domain-events")
def export_domain_events(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    aggregate_type: str | None = None,
    limit: int = Query(500, le=2000),
):
    require_module(ctx, "settings")
    return _audit_export.domain_events(db, aggregate_type=aggregate_type, limit=limit)
