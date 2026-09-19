"""Notification engine — templates, queueing, delivery, devices, audit."""

from porterchain_api.notification_engine.admin_service import NotificationAdminService
from porterchain_api.notification_engine.delivery_service import DeliveryService, deliver_notification
from porterchain_api.notification_engine.device_service import DeviceService
from porterchain_api.notification_engine.engine import NotificationEngine, get_notification_engine
from porterchain_api.notification_engine.fcm_service import FCMService
from porterchain_api.notification_engine.models import (
    NotificationDeliveryLog,
    NotificationDevice,
    NotificationPreference,
    NotificationRecord,
)
from porterchain_api.notification_engine.templates import TEMPLATES, render_template, template_meta

__all__ = [
    "DeliveryService",
    "DeviceService",
    "FCMService",
    "NotificationAdminService",
    "NotificationDeliveryLog",
    "NotificationDevice",
    "NotificationEngine",
    "NotificationPreference",
    "NotificationRecord",
    "TEMPLATES",
    "deliver_notification",
    "get_notification_engine",
    "render_template",
    "template_meta",
]
