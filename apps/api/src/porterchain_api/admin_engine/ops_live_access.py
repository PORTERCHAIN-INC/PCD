"""Who may watch the Ops Today live stream."""

from __future__ import annotations


def can_watch_dispatch(admin_user_id: str) -> bool:
    """Same gate as GET /live-map: SpiceDB ``dispatch_read`` for this staff user."""
    from porterchain_api.admin_engine.rbac import AdminContext, parse_admin_role, require_module
    from porterchain_api.admin_models import AdminUser
    from porterchain_api.db import SessionLocal

    db = SessionLocal()
    try:
        user = db.get(AdminUser, admin_user_id)
        if user is None or not getattr(user, "is_active", True):
            return False
        try:
            require_module(AdminContext(user=user, role=parse_admin_role(user.role or "")), "dispatch_read")
            return True
        except PermissionError:
            return False
    finally:
        db.close()
