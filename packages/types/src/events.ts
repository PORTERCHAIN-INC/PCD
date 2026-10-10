export type DomainEventType =
  | "visitor.created"
  | "visitor.session_started"
  | "visitor.session_merged"
  | "quote.created"
  | "quote.accepted"
  | "quote.expired"
  | "booking.started"
  | "booking.confirmed"
  | "checkout.started"
  | "checkout.abandoned"
  | "customer.registered"
  | "customer.authenticated"
  | "customer.reorder_nudge"
  | "merchant.lead_created"
  | "merchant.approved"
  | "merchant.activated"
  | "merchant.billed"
  | "payment.succeeded"
  | "payment.failed"
  | "order.created"
  | "order.booked"
  | "order.dispatch_ready"
  | "order.dispatch_requested"
  | "order.driver_assigned"
  | "order.driver_accepted"
  | "order.driver_rejected"
  | "order.arrived_pickup"
  | "order.pickup_completed"
  | "order.in_transit"
  | "order.delivered"
  | "order.pod_completed"
  | "order.invoiced"
  | "order.closed"
  | "order.cancelled"
  | "driver.payout_created"
  | "refund.requested"
  | "refund.issued"
  | "claim.opened"
  | "claim.resolved"
  | "notification.queued"
  | "notification.sent"
  | "webhook.received"
  | "fleetbase.order_created"
  | "fleetbase.status_updated"
  | "fleetbase.pod_received"
  | "fleetbase.sync_failed"
  | "lead.created"
  | "lead.merged"
  | "lead.engagement"
  | "lead.whatsapp_blocked";

export interface EventActor {
  type: string;
  id?: string;
}

export interface EventEnvelope<T = Record<string, unknown>> {
  eventId: string;
  eventType: DomainEventType | string;
  occurredAt: string;
  aggregateType: string;
  aggregateId: string;
  correlationId?: string;
  actor: EventActor;
  payload: T;
  version: number;
}
