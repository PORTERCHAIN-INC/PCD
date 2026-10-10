/** English words. Capacity class IDs are snake (SoT1). */

import {
  CAPACITY_CLASS_OPTIONS,
  vehicleLabel as capacityVehicleLabel,
} from "@porterchain/types/capacity";

export const VEHICLE_OPTIONS = CAPACITY_CLASS_OPTIONS;

export const PACKAGE_OPTIONS = [
  { id: "looseParcel", label: "Loose parcel" },
  { id: "documents", label: "Documents" },
  { id: "medical", label: "Medical" },
  { id: "furniture", label: "Furniture" },
  { id: "foodBeverage", label: "Food and beverage" },
] as const;

const ORDER_STATE_LABELS: Record<string, string> = {
  BOOKED: "Booked",
  DISPATCH_READY: "Ready for pickup",
  DRIVER_ASSIGNED: "Driver assigned",
  DRIVER_ACCEPTED: "Driver accepted",
  DRIVER_EN_ROUTE: "Driver on the way",
  AT_PICKUP: "At pickup",
  PICKED_UP: "Picked up",
  IN_TRANSIT: "In transit",
  AT_DESTINATION: "At destination",
  DELIVERED: "Delivered",
  POD_COMPLETED: "Proof of delivery",
  INVOICED: "Invoiced",
  CLOSED: "Closed",
  CANCELLED: "Cancelled",
  FAILED: "Failed",
  RETURN_TO_SENDER: "Returning to sender",
  DAMAGED: "Damaged",
  LOST: "Lost",
  CLAIM_OPEN: "Claim open",
  REFUNDED: "Refunded",
};

const PACKAGE_LABELS: Record<string, string> = Object.fromEntries(
  PACKAGE_OPTIONS.map((p) => [p.id, p.label])
);

const INVOICE_STATUS_LABELS: Record<string, string> = {
  none: "Not invoiced",
  generated: "Invoiced",
  draft: "Draft",
  pending: "Pending",
  sent: "Sent",
  paid: "Paid",
  overdue: "Overdue",
  void: "Void",
  partial: "Partially paid",
};

const CLAIM_STATUS_LABELS: Record<string, string> = {
  open: "Open",
  pending: "Pending",
  under_review: "Under review",
  approved: "Approved",
  denied: "Denied",
  closed: "Closed",
  resolved: "Resolved",
};

const CLAIM_TYPE_LABELS: Record<string, string> = {
  merchant_complaint: "Complaint",
  damaged_parcel: "Damaged parcel",
  lost_parcel: "Lost parcel",
  late_delivery: "Late delivery",
};

const PAYMENT_STATUS_LABELS: Record<string, string> = {
  pending: "Pending",
  succeeded: "Paid",
  paid: "Paid",
  failed: "Failed",
  refunded: "Refunded",
};

const SLA_STATUS_LABELS: Record<string, string> = {
  ok: "On time",
  at_risk: "At risk",
  breached: "Late",
};

const MODULE_LABELS: Record<string, string> = {
  dashboard: "Overview",
  book: "Booking",
  bulk: "Bulk upload",
  routes: "Route planner",
  api_keys: "Integrations",
  orders: "Orders",
  orders_write: "order changes",
  tracking: "Track",
  invoices: "Invoices",
  invoices_pay: "invoice payment",
  statements: "Statements",
  reports: "Reports",
  billing: "Billing",
  users: "Team",
  settings: "Company settings",
  support: "Inbox",
  claims: "Claims",
};

const TICKET_STATUS_LABELS: Record<string, string> = {
  open: "Open",
  pending: "Pending",
  waiting: "Waiting",
  closed: "Closed",
  resolved: "Resolved",
};

const MERCHANT_STATUS_LABELS: Record<string, string> = {
  PENDING: "Pending",
  ONBOARDING: "Onboarding",
  ACTIVE: "Active",
  SUSPENDED: "Suspended",
  CLOSED: "Closed",
};

const ONBOARDING_PHASE_LABELS: Record<string, string> = {
  ready: "Portal ready",
  needs_invite: "Needs invite",
  awaiting_clerk: "Awaiting sign-in",
  needs_activation: "User inactive",
  needs_approval: "Needs approval",
  onboarding: "Onboarding",
};

const SEAT_STATUS_LABELS: Record<string, string> = {
  pending: "Pending",
  active: "Active",
  off: "Off",
};

const ONBOARDING_STEP_STATUS_LABELS: Record<string, string> = {
  complete: "Complete",
  pending: "Pending",
  onboarding: "Onboarding",
  suspended: "Suspended",
  closed: "Closed",
  inactive: "Off",
  pending_review: "Pending review",
  waiting: "Waiting",
};

function pretty(key: string): string {
  const text = key.replace(/_/g, " ").trim();
  if (!text) return "—";
  return text.charAt(0).toUpperCase() + text.slice(1);
}

function lookup(map: Record<string, string>, key: string | null | undefined): string {
  if (!key) return "—";
  return map[key] || map[key.toLowerCase()] || pretty(key);
}

export function orderStateLabel(state: string | null | undefined): string {
  return lookup(ORDER_STATE_LABELS, state);
}

export function vehicleLabel(code: string | null | undefined): string {
  return capacityVehicleLabel(code);
}

export function packageLabel(code: string | null | undefined): string {
  return lookup(PACKAGE_LABELS, code);
}

export function invoiceStatusLabel(status: string | null | undefined): string {
  return lookup(INVOICE_STATUS_LABELS, status);
}

export function claimStatusLabel(status: string | null | undefined): string {
  return lookup(CLAIM_STATUS_LABELS, status);
}

export function claimTypeLabel(claimType: string | null | undefined): string {
  return lookup(CLAIM_TYPE_LABELS, claimType);
}

export function paymentStatusLabel(status: string | null | undefined): string {
  return lookup(PAYMENT_STATUS_LABELS, status);
}

export function slaStatusLabel(status: string | null | undefined): string {
  return lookup(SLA_STATUS_LABELS, status);
}

export function ticketStatusLabel(status: string | null | undefined): string {
  return lookup(TICKET_STATUS_LABELS, status);
}

export function merchantStatusLabel(status: string | null | undefined): string {
  if (!status) return "Unknown";
  return (
    MERCHANT_STATUS_LABELS[status] || MERCHANT_STATUS_LABELS[status.toUpperCase()] || pretty(status)
  );
}

export function onboardingPhaseLabel(phase: string | null | undefined): string {
  return lookup(ONBOARDING_PHASE_LABELS, phase);
}

export function seatStatusLabel(status: string | null | undefined): string {
  return lookup(SEAT_STATUS_LABELS, status);
}

export function onboardingStepStatusLabel(
  status: string | null | undefined,
  complete?: boolean
): string {
  if (complete || status === "complete") return "Complete";
  return lookup(ONBOARDING_STEP_STATUS_LABELS, status);
}

const MODULE_JOB: Record<string, string> = {
  book: "Dispatcher",
  bulk: "Dispatcher",
  routes: "Dispatcher",
  orders_write: "Dispatcher",
  billing: "Accounting",
  invoices: "Accounting",
  invoices_pay: "Accounting",
  statements: "Accounting",
  reports: "Accounting",
  users: "Manager",
  api_keys: "Manager",
  settings: "Manager",
};

export function moduleLabel(module: string | null | undefined): string {
  if (!module) return "this page";
  return MODULE_LABELS[module] ?? pretty(module);
}

export function forbiddenModuleMessage(module: string | null | undefined): string {
  const job = module ? MODULE_JOB[module] : undefined;
  if (job) return `Ask your owner for ${job} access.`;
  return `Ask your owner for access to ${moduleLabel(module)}.`;
}

const ORDER_SOURCE_LABELS: Record<string, string> = {
  WEBSITE: "Customer",
  MERCHANT: "Merchant",
  API: "API",
  CSV: "CSV",
  ADMIN: "Admin",
  PHONE: "Phone",
  PARTNER: "Partner",
  SHOPIFY: "Shopify",
};

export function orderSourceLabel(source: string | null | undefined): string {
  if (!source) return "—";
  return ORDER_SOURCE_LABELS[source] ?? pretty(source);
}
