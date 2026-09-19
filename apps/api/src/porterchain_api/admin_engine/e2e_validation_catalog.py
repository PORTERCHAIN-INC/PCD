"""Enterprise E2E validation catalog — phases, steps, events, failure scenarios (masterrule §16)."""

from __future__ import annotations

from typing import Literal

ValidationStatus = Literal["PASS", "WARNING", "FAIL", "BLOCKER"]

SYSTEM_CHAIN: tuple[dict[str, str], ...] = (
    {"id": "website", "label": "Website"},
    {"id": "booking_portal", "label": "Booking Portal"},
    {"id": "customer_portal", "label": "Customer Portal"},
    {"id": "merchant_portal", "label": "Merchant Portal"},
    {"id": "admin_portal", "label": "Admin Portal"},
    {"id": "porterchain_api", "label": "Porterchain API"},
    {"id": "pricing_engine", "label": "Pricing Engine"},
    {"id": "billing_engine", "label": "Billing Engine"},
    {"id": "notification_engine", "label": "Notification Engine"},
    {"id": "orders_engine", "label": "Orders Engine"},
    {"id": "crm_engine", "label": "CRM Engine"},
    {"id": "finance_engine", "label": "Finance Engine"},
    {"id": "claims_engine", "label": "Claims Engine"},
    {"id": "support_engine", "label": "Support Engine"},
    {"id": "event_bus", "label": "Internal Event Bus"},
    {"id": "fleetbase_adapter", "label": "Fleetbase Adapter"},
    {"id": "fleetbase", "label": "Fleetbase"},
    {"id": "driver_mobile", "label": "Driver Mobile"},
)

FORWARD_LOGISTICS_STEPS: tuple[str, ...] = (
    "Website Visitor",
    "Quote",
    "Booking Draft",
    "Collect Email",
    "Collect Phone",
    "Booking Draft Saved",
    "Clerk Authentication",
    "Booking Draft Restored",
    "Booking Review",
    "Stripe Sandbox Payment",
    "Webhook Verification",
    "Payment Verified",
    "Order Created",
    "Pricing Engine",
    "Billing Engine",
    "Operations Queue",
    "Vehicle Recommendation",
    "Driver Recommendation",
    "Route Optimization",
    "Fleetbase Adapter",
    "Fleetbase Dispatch",
    "Driver Assigned",
    "Driver Accepted",
    "Pickup",
    "Transit",
    "Near Delivery",
    "Delivered",
    "Photo",
    "Signature",
    "OTP",
    "Proof Of Delivery",
    "Invoice",
    "Receipt",
    "Push Notification",
    "Customer Dashboard Updated",
    "Merchant Updated",
    "Reports Updated",
)

MERCHANT_SCENARIO_STEPS: tuple[str, ...] = (
    "Merchant Login",
    "CSV Upload",
    "100 Orders",
    "Contract Pricing",
    "Operations Queue",
    "Optimization",
    "Dispatch",
    "Delivery",
    "Billing Run",
    "Invoice",
    "Statement",
    "Reports",
)

REVERSE_LOGISTICS_FLOW: tuple[str, ...] = (
    "Delivered",
    "Customer Rejects",
    "Return Requested",
    "Return Approved",
    "Driver Assigned",
    "Return Pickup",
    "Warehouse",
    "Merchant",
    "Refund",
    "Return Completed",
)

REVERSE_EXCEPTION_SCENARIOS: tuple[dict[str, str], ...] = (
    {"id": "customer_refused", "label": "Customer Refused", "claim_type": "delivery_failed"},
    {"id": "wrong_address", "label": "Wrong Address", "claim_type": "wrong_delivery"},
    {"id": "damaged_parcel", "label": "Damaged Parcel", "claim_type": "damaged_parcel"},
    {"id": "lost_parcel", "label": "Lost Parcel", "claim_type": "lost_parcel"},
    {"id": "wrong_parcel", "label": "Wrong Parcel", "claim_type": "wrong_delivery"},
    {"id": "merchant_recall", "label": "Merchant Recall", "claim_type": "merchant_complaint"},
)

FAILURE_SCENARIOS: tuple[str, ...] = (
    "authentication_failed",
    "payment_failed",
    "stripe_webhook_failure",
    "driver_rejects",
    "driver_cancels",
    "vehicle_breakdown",
    "driver_offline",
    "fleetbase_offline",
    "fleetbase_adapter_failure",
    "google_maps_failure",
    "osrm_failure",
    "valhalla_failure",
    "redis_restart",
    "postgresql_restart",
    "firebase_failure",
    "websocket_failure",
    "notification_failure",
    "customer_cancels",
    "merchant_cancels",
    "pickup_failed",
    "delivery_failed",
    "customer_not_home",
    "otp_failed",
    "signature_failed",
    "photo_upload_failed",
    "pod_failed",
)

REQUIRED_EVENTS: tuple[dict[str, str], ...] = (
    {"alias": "BookingDraftCreated", "event_type": "booking_draft.draft_created", "publisher": "booking_engine"},
    {"alias": "CustomerAuthenticated", "event_type": "customer.authenticated", "publisher": "booking_engine"},
    {"alias": "PaymentSucceeded", "event_type": "payment.succeeded", "publisher": "billing_engine"},
    {"alias": "OrderCreated", "event_type": "order.created", "publisher": "booking_engine"},
    {"alias": "DriverAssigned", "event_type": "order.driver_assigned", "publisher": "fleetbase_engine"},
    {"alias": "DriverAccepted", "event_type": "order.driver_accepted", "publisher": "fleetbase_engine"},
    {"alias": "PickupStarted", "event_type": "order.arrived_pickup", "publisher": "fleetbase_engine"},
    {"alias": "PickedUp", "event_type": "order.pickup_completed", "publisher": "fleetbase_engine"},
    {"alias": "LocationUpdated", "event_type": "order.tracking_updated", "publisher": "fleetbase_engine"},
    {"alias": "NearDelivery", "event_type": "order.near_delivery", "publisher": "fleetbase_engine"},
    {"alias": "Delivered", "event_type": "order.delivered", "publisher": "fleetbase_engine"},
    {"alias": "PODCompleted", "event_type": "order.pod_completed", "publisher": "fleetbase_engine"},
    {"alias": "InvoiceGenerated", "event_type": "order.invoiced", "publisher": "billing_engine"},
    {"alias": "ReturnRequested", "event_type": "refund.requested", "publisher": "admin_engine"},
    {"alias": "ReturnApproved", "event_type": "refund.approved", "publisher": "admin_engine"},
    {"alias": "RefundCompleted", "event_type": "refund.issued", "publisher": "billing_engine"},
    {"alias": "NotificationSent", "event_type": "notification.sent", "publisher": "notification_engine"},
)

NOTIFICATION_AUDIENCES: tuple[str, ...] = (
    "customer",
    "merchant",
    "driver",
    "admin",
    "operations",
    "finance",
    "support",
)

CONSISTENCY_SURFACES: tuple[str, ...] = (
    "website_status",
    "customer_dashboard",
    "merchant_dashboard",
    "admin_orders",
    "operations_queue",
    "fleetbase",
    "driver_app",
    "reports",
    "billing",
    "finance",
    "claims",
    "notifications",
)

E2E_REPORT_FILES: tuple[str, ...] = (
    "SYSTEM_VALIDATION_REPORT.md",
    "FORWARD_LOGISTICS_REPORT.md",
    "REVERSE_LOGISTICS_REPORT.md",
    "FAILURE_SCENARIOS_REPORT.md",
    "EVENT_BUS_REPORT.md",
    "NOTIFICATION_REPORT.md",
    "FLEETBASE_SYNC_REPORT.md",
    "DATA_CONSISTENCY_REPORT.md",
    "API_TRACE_REPORT.md",
    "PRODUCTION_READINESS_REPORT.md",
)

E2E_MARKER = "e2e-validation-v1"
DEFAULT_MERCHANT_BULK_COUNT = 100
