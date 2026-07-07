import { z } from "zod";
import { adminFetch } from "@/lib/api";

export const TICKET_CATEGORIES = [
  "general_inquiry",
  "booking_issue",
  "quote_issue",
  "tracking_issue",
  "pickup_issue",
  "delivery_issue",
  "late_delivery",
  "lost_parcel",
  "damaged_parcel",
  "wrong_delivery",
  "billing_issue",
  "invoice_issue",
  "payment_issue",
  "refund_request",
  "merchant_support",
  "driver_support",
  "fleet_issue",
  "technical_issue",
  "api_support",
  "account_issue",
  "complaint",
  "suggestion",
  "claim",
  "internal_request",
  "compliance",
  "other",
] as const;

export const TICKET_STATUSES = [
  "new",
  "open",
  "assigned",
  "waiting_customer",
  "waiting_merchant",
  "waiting_driver",
  "waiting_internal",
  "escalated",
  "resolved",
  "closed",
  "archived",
] as const;

export const TICKET_PRIORITIES = ["low", "normal", "high", "urgent", "critical"] as const;

const ticketRowSchema = z.object({
  id: z.string(),
  ticket_number: z.string(),
  subject: z.string(),
  category: z.string(),
  priority: z.string(),
  status: z.string(),
  display_status: z.string(),
  customer_id: z.string().nullable().optional(),
  customer_email: z.string().nullable().optional(),
  merchant_id: z.string().nullable().optional(),
  merchant_name: z.string().nullable().optional(),
  driver_id: z.string().nullable().optional(),
  driver_name: z.string().nullable().optional(),
  order_id: z.string().nullable().optional(),
  order_number: z.string().nullable().optional(),
  tracking_number: z.string().nullable().optional(),
  booking_id: z.string().nullable().optional(),
  booking_number: z.string().nullable().optional(),
  assigned_agent_id: z.string().nullable().optional(),
  assigned_agent: z.string().nullable().optional(),
  sla_status: z.string(),
  description: z.string().nullable().optional(),
  created_at: z.string(),
  updated_at: z.string(),
});

export type TicketRow = z.infer<typeof ticketRowSchema>;

export const ticketDetailSchema = ticketRowSchema.extend({
  timeline: z.array(z.record(z.string(), z.unknown())),
  communications: z.array(z.record(z.string(), z.unknown())),
  internal_notes: z.array(z.record(z.string(), z.unknown())),
  attachments: z.array(z.record(z.string(), z.unknown())),
  customer: z.record(z.string(), z.unknown()).nullable().optional(),
  merchant: z.record(z.string(), z.unknown()).nullable().optional(),
  driver: z.record(z.string(), z.unknown()).nullable().optional(),
  order: z.record(z.string(), z.unknown()).nullable().optional(),
  booking: z.record(z.string(), z.unknown()).nullable().optional(),
  tracking: z.record(z.string(), z.unknown()).nullable().optional(),
  invoice: z.record(z.string(), z.unknown()).nullable().optional(),
  payment: z.record(z.string(), z.unknown()).nullable().optional(),
  claims: z.array(z.record(z.string(), z.unknown())),
  documents: z.array(z.record(z.string(), z.unknown())),
  domain_events: z.array(z.record(z.string(), z.unknown())),
  audit_log: z.array(z.record(z.string(), z.unknown())),
  sla: z.record(z.string(), z.unknown()),
  duplicates: z.array(z.record(z.string(), z.unknown())),
  smart: z.record(z.string(), z.unknown()),
});

export type TicketDetail = z.infer<typeof ticketDetailSchema>;

export type SupportDashboard = {
  open_tickets: number;
  urgent_tickets: number;
  sla_breaches: number;
  pending_customer: number;
  pending_merchant: number;
  pending_driver: number;
  pending_internal: number;
  claims_linked: number;
  orders_impacted: number;
  avg_first_response_hours: number;
  avg_resolution_hours: number;
  customer_satisfaction: number;
  recent_activity: Array<Record<string, unknown>>;
  team_workload: Array<Record<string, unknown>>;
};

export type SupportFilters = {
  status?: string;
  category?: string;
  priority?: string;
  agent_id?: string;
  merchant_id?: string;
  driver_id?: string;
  customer_id?: string;
  sla?: string;
  module?: string;
  search?: string;
  date_from?: string;
  date_to?: string;
  limit?: number;
};

const B = "/v1/admin/support";

function qs(filters?: SupportFilters): string {
  if (!filters) return "";
  const p = new URLSearchParams();
  Object.entries(filters).forEach(([k, v]) => {
    if (v !== undefined && v !== "") p.set(k, String(v));
  });
  const q = p.toString();
  return q ? `?${q}` : "";
}

export const supportApi = {
  list: async (token: string, filters?: SupportFilters) => {
    const raw = await adminFetch<unknown[]>(`${B}/tickets${qs(filters)}`, token);
    return z.array(ticketRowSchema).parse(raw);
  },
  dashboard: (token: string) => adminFetch<SupportDashboard>(`${B}/dashboard`, token),
  reports: (token: string) => adminFetch<Record<string, unknown>>(`${B}/reports`, token),
  detail: async (token: string, id: string) => {
    const raw = await adminFetch<unknown>(`${B}/tickets/${id}`, token);
    return ticketDetailSchema.parse(raw);
  },
  create: (
    token: string,
    body: {
      subject: string;
      description?: string;
      priority?: string;
      category?: string;
      order_id?: string;
      customer_id?: string;
      merchant_id?: string;
      driver_id?: string;
    }
  ) =>
    adminFetch<TicketRow>(`${B}/tickets`, token, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  updateStatus: (token: string, id: string, status: string) =>
    adminFetch<TicketDetail>(`${B}/tickets/${id}/status`, token, {
      method: "POST",
      body: JSON.stringify({ status }),
    }),
  assign: (token: string, id: string, agentId: string) =>
    adminFetch<TicketDetail>(`${B}/tickets/${id}/assign`, token, {
      method: "POST",
      body: JSON.stringify({ agent_id: agentId }),
    }),
  autoAssign: (token: string, id: string) =>
    adminFetch<TicketDetail>(`${B}/tickets/${id}/auto-assign`, token, { method: "POST" }),
  addNote: (token: string, id: string, body: string, internal = true, channel = "note") =>
    adminFetch<TicketDetail>(`${B}/tickets/${id}/notes`, token, {
      method: "POST",
      body: JSON.stringify({ body, internal, channel }),
    }),
  pauseSla: (token: string, id: string) =>
    adminFetch<TicketDetail>(`${B}/tickets/${id}/sla/pause`, token, { method: "POST" }),
  resumeSla: (token: string, id: string) =>
    adminFetch<TicketDetail>(`${B}/tickets/${id}/sla/resume`, token, { method: "POST" }),
  bulk: (
    token: string,
    ticketIds: string[],
    action: string,
    opts?: { agent_id?: string; status?: string }
  ) =>
    adminFetch<{ results: Array<{ ticket_id: string; status: string }> }>(`${B}/bulk`, token, {
      method: "POST",
      body: JSON.stringify({ ticket_ids: ticketIds, action, ...opts }),
    }),
  knowledgeBase: (token: string) =>
    adminFetch<Record<string, unknown>>(`${B}/knowledge-base`, token),
  saveArticle: (token: string, article: Record<string, unknown>) =>
    adminFetch<Record<string, unknown>>(`${B}/knowledge-base/articles`, token, {
      method: "POST",
      body: JSON.stringify(article),
    }),
  macros: (token: string) => adminFetch<Array<Record<string, unknown>>>(`${B}/macros`, token),
  saveMacro: (token: string, macro: Record<string, unknown>) =>
    adminFetch<Record<string, unknown>>(`${B}/macros`, token, {
      method: "POST",
      body: JSON.stringify(macro),
    }),
  automation: (token: string) => adminFetch<Record<string, unknown>>(`${B}/automation`, token),
  saveAutomation: (token: string, rules: Record<string, unknown>) =>
    adminFetch<Record<string, unknown>>(`${B}/automation`, token, {
      method: "POST",
      body: JSON.stringify(rules),
    }),
  slaConfig: (token: string) => adminFetch<Record<string, unknown>>(`${B}/settings/sla`, token),
  saveSlaConfig: (token: string, config: Record<string, unknown>) =>
    adminFetch<Record<string, unknown>>(`${B}/settings/sla`, token, {
      method: "POST",
      body: JSON.stringify(config),
    }),
};

export const STATUS_STYLES: Record<string, string> = {
  new: "bg-blue-100 text-blue-700",
  open: "bg-blue-100 text-blue-700",
  assigned: "bg-violet-100 text-violet-700",
  waiting_customer: "bg-amber-100 text-amber-800",
  waiting_merchant: "bg-orange-100 text-orange-800",
  waiting_driver: "bg-yellow-100 text-yellow-800",
  waiting_internal: "bg-gray-100 text-gray-700",
  escalated: "bg-red-100 text-red-700",
  resolved: "bg-green-100 text-green-700",
  closed: "bg-gray-100 text-gray-600",
  archived: "bg-gray-100 text-gray-500",
  in_progress: "bg-violet-100 text-violet-700",
};

export const PRIORITY_STYLES: Record<string, string> = {
  low: "bg-gray-100 text-gray-600",
  normal: "bg-blue-50 text-blue-700",
  high: "bg-amber-100 text-amber-800",
  urgent: "bg-orange-100 text-orange-800",
  critical: "bg-red-100 text-red-700",
};

export const SLA_STYLES: Record<string, string> = {
  ok: "bg-green-100 text-green-700",
  met: "bg-green-100 text-green-700",
  at_risk: "bg-amber-100 text-amber-800",
  breached: "bg-red-100 text-red-700",
  paused: "bg-gray-100 text-gray-600",
};

export function formatCategory(c: string) {
  return c.replace(/_/g, " ");
}

export function exportTicketsCsv(rows: TicketRow[], filename = "support-tickets.csv") {
  const headers = [
    "ticket_number",
    "subject",
    "category",
    "priority",
    "status",
    "customer_email",
    "merchant_name",
    "driver_name",
    "order_number",
    "tracking_number",
    "assigned_agent",
    "sla_status",
    "created_at",
  ];
  const lines = [
    headers.join(","),
    ...rows.map((r) =>
      headers
        .map((h) => {
          const v = r[h as keyof TicketRow];
          const s = v == null ? "" : String(v);
          return s.includes(",") ? `"${s.replace(/"/g, '""')}"` : s;
        })
        .join(",")
    ),
  ];
  const blob = new Blob([lines.join("\n")], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
