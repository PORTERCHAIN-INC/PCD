"""Porterchain Fleetbase sync engine.

Event-driven Merchant → Fleetbase communication. A merchant never talks to
Fleetbase directly; every booking flows through the Porterchain logistics engine
and the Fleetbase adapter. Components:

- MerchantSyncService   — pre-dispatch validation gate (merchant/pricing/contract/terms)
- BookingSyncService    — outbound order/driver/cancellation/return/damage/claim sync
- WebhookProcessor      — inbound status/tracking/POD/driver/exception/claim sync
- StatusTranslator      — Fleetbase status/event ↔ Porterchain OrderState
- TrackingTranslator    — Fleetbase tracker → Porterchain tracking shape
- TrackingFacade        — single fetch + normalize path for all portal tracking
- RetryQueue / ErrorQueue — durable retry + dead-letter
- AuditLogger           — immutable sync audit trail
"""

from porterchain_api.fleetbase_engine.audit_logger import AuditLogger
from porterchain_api.fleetbase_engine.bond import run_boot_handshake, verify_fleetbase_bond
from porterchain_api.fleetbase_engine.booking_sync_service import BookingSyncService
from porterchain_api.fleetbase_engine.merchant_sync_service import (
    BookingValidationError,
    MerchantSyncService,
    ValidatedBooking,
)
from porterchain_api.fleetbase_engine.retry_queue import ErrorQueue, RetryQueue
from porterchain_api.fleetbase_engine.status_translator import StatusTranslator
from porterchain_api.fleetbase_engine.tracking_facade import TrackingFacade
from porterchain_api.fleetbase_engine.tracking_translator import TrackingTranslator
from porterchain_api.fleetbase_engine.webhook_ingress_service import WebhookIngressService
from porterchain_api.fleetbase_engine.webhook_processor import WebhookProcessor

__all__ = [
    "AuditLogger",
    "BookingSyncService",
    "BookingValidationError",
    "ErrorQueue",
    "MerchantSyncService",
    "RetryQueue",
    "StatusTranslator",
    "TrackingFacade",
    "TrackingTranslator",
    "ValidatedBooking",
    "WebhookIngressService",
    "WebhookProcessor",
    "run_boot_handshake",
    "verify_fleetbase_bond",
]
