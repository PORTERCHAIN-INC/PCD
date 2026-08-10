/** Canonical domain event type constants — mirrors shared/python catalog. */
export const CATALOG_VERSION = "1.0.0";

export const DomainEvents = {
  // Visitor
  VISITOR_CREATED: "visitor.created",
  VISITOR_SESSION_STARTED: "visitor.session_started",
  SESSION_MERGED: "visitor.session_merged",

  // Quote & booking
  QUOTE_CREATED: "quote.created",
  QUOTE_ACCEPTED: "quote.accepted",
  QUOTE_EXPIRED: "quote.expired",
  BOOKING_STARTED: "booking.started",
  BOOKING_CONFIRMED: "booking.confirmed",
  CHECKOUT_STARTED: "checkout.started",
  CHECKOUT_ABANDONED: "checkout.abandoned",

  // Customer
  CUSTOMER_REGISTERED: "customer.registered",
  CUSTOMER_AUTHENTICATED: "customer.authenticated",

  // Merchant
  MERCHANT_LEAD_CREATED: "merchant.lead_created",
  MERCHANT_APPROVED: "merchant.approved",
  MERCHANT_ACTIVATED: "merchant.activated",
  MERCHANT_SUSPENDED: "merchant.suspended",
  MERCHANT_BILLED: "merchant.billed",

  // Payment
  PAYMENT_STARTED: "payment.started",
  PAYMENT_SUCCEEDED: "payment.succeeded",
  PAYMENT_FAILED: "payment.failed",

  // Orders
  ORDER_CREATED: "order.created",
  ORDER_BOOKED: "order.booked",
  ORDER_DISPATCH_READY: "order.dispatch_ready",
  DISPATCH_REQUESTED: "order.dispatch_requested",
  DRIVER_ASSIGNED: "order.driver_assigned",
  DRIVER_ACCEPTED: "order.driver_accepted",
  DRIVER_ARRIVED_PICKUP: "order.arrived_pickup",
  PARCEL_PICKED_UP: "order.pickup_completed",
  DELIVERY_STARTED: "order.in_transit",
  PARCEL_DELIVERED: "order.delivered",
  PROOF_COMPLETED: "order.pod_completed",
  INVOICE_GENERATED: "order.invoiced",
  ORDER_CLOSED: "order.closed",
  ORDER_CANCELLED: "order.cancelled",
  DRIVER_REJECTED: "order.driver_rejected",
  ORDER_NEAR_DELIVERY: "order.near_delivery",
  ORDER_LOCATION_UPDATED: "order.tracking_updated",
  ORDER_TEMP_EXCURSION: "order.temp_excursion",

  // Phase 2 stubs (ADR-010 — no consumers yet)
  ROUTE_OPTIMIZED: "route.optimized",
  DISPATCH_RECOMMENDATION: "dispatch.recommendation",
  ETA_PREDICTED: "eta.predicted",

  // Financial
  REFUND_REQUESTED: "refund.requested",
  REFUND_ISSUED: "refund.issued",
  DRIVER_PAYOUT_CREATED: "driver.payout_created",

  // Claims
  CLAIM_OPENED: "claim.opened",
  CLAIM_RESOLVED: "claim.resolved",

  // Support
  SUPPORT_TICKET_CREATED: "support.ticket_created",
  PRIVACY_DELETE_REQUESTED: "privacy.delete_requested",

  // Booking draft
  BOOKING_DRAFT_CREATED: "booking_draft.draft_created",

  // Notifications & webhooks
  NOTIFICATION_QUEUED: "notification.queued",
  NOTIFICATION_SENT: "notification.sent",
  WEBHOOK_RECEIVED: "webhook.received",

  // Fleetbase
  FLEETBASE_ORDER_CREATED: "fleetbase.order_created",
  FLEETBASE_STATUS_UPDATED: "fleetbase.status_updated",
  FLEETBASE_POD_RECEIVED: "fleetbase.pod_received",
  FLEETBASE_SYNC_FAILED: "fleetbase.sync_failed",

  // CRM
  LEAD_CREATED: "lead.created",
} as const;

export type DomainEventName = (typeof DomainEvents)[keyof typeof DomainEvents];

/** PascalCase aliases for documentation / codegen */
export const EventAliases: Record<string, DomainEventName> = {
  VisitorCreated: DomainEvents.VISITOR_CREATED,
  QuoteCreated: DomainEvents.QUOTE_CREATED,
  QuoteAccepted: DomainEvents.QUOTE_ACCEPTED,
  CustomerRegistered: DomainEvents.CUSTOMER_REGISTERED,
  CustomerAuthenticated: DomainEvents.CUSTOMER_AUTHENTICATED,
  PaymentStarted: DomainEvents.PAYMENT_STARTED,
  MerchantApproved: DomainEvents.MERCHANT_APPROVED,
  MerchantSuspended: DomainEvents.MERCHANT_SUSPENDED,
  PaymentSucceeded: DomainEvents.PAYMENT_SUCCEEDED,
  BookingConfirmed: DomainEvents.BOOKING_CONFIRMED,
  OrderCreated: DomainEvents.ORDER_CREATED,
  FleetbaseOrderCreated: DomainEvents.FLEETBASE_ORDER_CREATED,
  BookingDraftCreated: DomainEvents.BOOKING_DRAFT_CREATED,
  SupportTicketCreated: DomainEvents.SUPPORT_TICKET_CREATED,
  PickupStarted: DomainEvents.DRIVER_ARRIVED_PICKUP,
  PickedUp: DomainEvents.PARCEL_PICKED_UP,
  Delivered: DomainEvents.PARCEL_DELIVERED,
  PODCompleted: DomainEvents.PROOF_COMPLETED,
  NearDelivery: DomainEvents.ORDER_NEAR_DELIVERY,
  LocationUpdated: DomainEvents.ORDER_LOCATION_UPDATED,
  RouteOptimized: DomainEvents.ROUTE_OPTIMIZED,
  FleetbaseSync: DomainEvents.FLEETBASE_STATUS_UPDATED,
  DispatchRequested: DomainEvents.DISPATCH_REQUESTED,
  DriverAssigned: DomainEvents.DRIVER_ASSIGNED,
  DriverAccepted: DomainEvents.DRIVER_ACCEPTED,
  DriverArrivedPickup: DomainEvents.DRIVER_ARRIVED_PICKUP,
  ParcelPickedUp: DomainEvents.PARCEL_PICKED_UP,
  DeliveryStarted: DomainEvents.DELIVERY_STARTED,
  ParcelDelivered: DomainEvents.PARCEL_DELIVERED,
  ProofCompleted: DomainEvents.PROOF_COMPLETED,
  InvoiceGenerated: DomainEvents.INVOICE_GENERATED,
  MerchantBilled: DomainEvents.MERCHANT_BILLED,
  DriverPayoutCreated: DomainEvents.DRIVER_PAYOUT_CREATED,
  RefundRequested: DomainEvents.REFUND_REQUESTED,
  ClaimOpened: DomainEvents.CLAIM_OPENED,
  ClaimResolved: DomainEvents.CLAIM_RESOLVED,
  NotificationQueued: DomainEvents.NOTIFICATION_QUEUED,
  NotificationSent: DomainEvents.NOTIFICATION_SENT,
  WebhookReceived: DomainEvents.WEBHOOK_RECEIVED,
};
