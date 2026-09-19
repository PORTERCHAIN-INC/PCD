"""Admin operational driver notify + CRM activity (push / SMS / email)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.admin_engine.crm_sales_service import CrmSalesService
from porterchain_api.db import db_transaction

ACTION_LABEL = {
    "push": "Push notification sent",
    "sms": "SMS sent",
    "email": "Email sent",
}

_crm = CrmSalesService()


def run_admin_driver_action(
    db: Session,
    driver: Any,
    action_type: str,
    message: str | None,
    actor_id: str | None = None,
) -> dict[str, Any]:
    if action_type in ("request_documents", "reset_password"):
        raise NotImplementedError(f"{action_type}_not_implemented")

    delivery_status = "queued"
    delivery_detail: str | None = None
    text = message or "You have a new notification from operations."
    email_text = message or "Message from Porterchain operations."

    if action_type == "push":
        from porterchain_api.notification_engine.fcm_service import firebase_credentials_configured
        from porterchain_driver.platform import DriverPlatform
        from porterchain_shared.config.settings import get_platform_settings

        ps = get_platform_settings()
        if not getattr(ps, "push_enabled", True):
            delivery_status, delivery_detail = "logged", "push_disabled"
        elif not getattr(ps, "push_send", True) or not firebase_credentials_configured():
            delivery_status, delivery_detail = "logged", "push_log_only"
        DriverPlatform().push.notify_driver(
            db,
            driver,
            title="Message from Porterchain",
            body=text,
        )
    elif action_type == "email" and driver.email:
        from porterchain_api.notification_engine.engine import get_notification_engine

        get_notification_engine().dispatch(
            db,
            event_type="admin.driver_action",
            template_key="delivery_update",
            channel="email",
            recipient_type="driver",
            recipient_id=driver.id,
            recipient_address=driver.email,
            context={"message": email_text},
        )
    elif action_type == "sms" and driver.phone:
        from porterchain_api.notification_engine.engine import get_notification_engine
        from porterchain_shared.config.settings import get_platform_settings

        ps = get_platform_settings()
        if not getattr(ps, "sms_enabled", False):
            delivery_status, delivery_detail = "logged", "sms_disabled"
        elif not (getattr(ps, "sms_provider", "") or "").strip():
            delivery_status, delivery_detail = "logged", "sms_provider_missing"
        get_notification_engine().dispatch(
            db,
            event_type="admin.driver_action",
            template_key="delivery_update",
            channel="sms",
            recipient_type="driver",
            recipient_id=driver.id,
            recipient_address=driver.phone,
            context={"message": email_text},
        )
    elif action_type == "email" and not driver.email:
        raise ValueError("driver_email_missing")
    elif action_type == "sms" and not driver.phone:
        raise ValueError("driver_phone_missing")
    elif action_type not in ("push", "email", "sms"):
        raise ValueError("unsupported_driver_action")

    subject = ACTION_LABEL.get(action_type, action_type)
    if delivery_status == "logged":
        subject = f"{subject} (log-only — not delivered)"
    with db_transaction(db):
        _crm.log_activity(
            db,
            entity_type="driver",
            entity_id=driver.id,
            activity_type="email" if action_type == "email" else "system",
            subject=subject,
            body=message,
            actor_id=actor_id,
        )
    return {
        "ok": True,
        "action": action_type,
        "delivery_status": delivery_status,
        "detail": delivery_detail,
    }
