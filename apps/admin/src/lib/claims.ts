import { z } from "zod";
import { adminFetch } from "@/lib/api";

export const CLAIM_TYPES = [
  "lost_parcel",
  "damaged_parcel",
  "missing_items",
  "wrong_delivery",
  "late_delivery",
  "pickup_failed",
  "delivery_failed",
  "customer_complaint",
  "merchant_complaint",
  "driver_complaint",
  "vehicle_damage",
  "insurance_claim",
  "payment_dispute",
  "chargeback",
  "fraud_investigation",
  "internal_investigation",
  "compliance_issue",
  "other",
] as const;

export const CLAIM_STATUSES = [
  "new",
  "assigned",
  "under_investigation",
  "waiting_customer",
  "waiting_merchant",
  "waiting_driver",
  "waiting_insurance",
  "approved",
  "rejected",
  "compensated",
  "closed",
  "archived",
] as const;

const claimRowSchema = z.object({
  id: z.string(),
  claim_number: z.string(),
  claim_type: z.string(),
  priority: z.string(),
  status: z.string(),
  display_status: z.string(),
  merchant_id: z.string().nullable().optional(),
  merchant_name: z.string().nullable().optional(),
  customer_id: z.string().nullable().optional(),
  customer_email: z.string().nullable().optional(),
  driver_id: z.string().nullable().optional(),
  driver_name: z.string().nullable().optional(),
  order_id: z.string(),
  tracking_number: z.string().nullable().optional(),
  order_number: z.string().nullable().optional(),
  amount_cents: z.number(),
  has_insurance: z.boolean(),
  assigned_investigator_id: z.string().nullable().optional(),
  assigned_investigator: z.string().nullable().optional(),
  risk_score: z.number(),
  description: z.string().nullable().optional(),
  created_at: z.string(),
  updated_at: z.string(),
  resolved_at: z.string().nullable().optional(),
});

export type ClaimRow = z.infer<typeof claimRowSchema>;

export const claimDetailSchema = claimRowSchema.extend({
  evidence_files: z.array(z.record(z.string(), z.unknown())),
  communications: z.array(z.record(z.string(), z.unknown())),
  investigation: z.record(z.string(), z.unknown()),
  internal_notes: z.array(z.record(z.string(), z.unknown())),
  timeline: z.array(z.record(z.string(), z.unknown())),
  compensation: z.record(z.string(), z.unknown()),
  insurance: z.record(z.string(), z.unknown()),
  order: z.record(z.string(), z.unknown()),
  domain_events: z.array(z.record(z.string(), z.unknown())),
  duplicates: z.array(z.record(z.string(), z.unknown())),
  smart: z.record(z.string(), z.unknown()),
});

export type ClaimDetail = z.infer<typeof claimDetailSchema>;

export type ClaimDashboard = {
  open_claims: number;
  under_investigation: number;
  waiting_merchant: number;
  waiting_customer: number;
  waiting_driver: number;
  insurance_claims: number;
  chargebacks: number;
  resolved_claims: number;
  rejected_claims: number;
  avg_resolution_hours: number;
  total_compensation_cents: number;
  monthly_claims: number;
  avg_risk_score: number;
};

export type ClaimFilters = {
  status?: string;
  claim_type?: string;
  priority?: string;
  search?: string;
  merchant_id?: string;
  driver_id?: string;
  customer_id?: string;
  insurance?: boolean;
  date_from?: string;
  date_to?: string;
  amount_min_cents?: number;
  amount_max_cents?: number;
  risk_min?: number;
};

const B = "/v1/admin/claims";

function qs(filters?: ClaimFilters): string {
  if (!filters) return "";
  const p = new URLSearchParams();
  Object.entries(filters).forEach(([k, v]) => {
    if (v !== undefined && v !== "") p.set(k, String(v));
  });
  const q = p.toString();
  return q ? `?${q}` : "";
}

export const claimsApi = {
  list: async (token: string, filters?: ClaimFilters) => {
    const raw = await adminFetch<unknown[]>(`${B}${qs(filters)}`, token);
    return z.array(claimRowSchema).parse(raw);
  },
  dashboard: (token: string) => adminFetch<ClaimDashboard>(`${B}/dashboard`, token),
  reports: (token: string) => adminFetch<Record<string, unknown>>(`${B}/reports`, token),
  detail: async (token: string, id: string) => {
    const raw = await adminFetch<unknown>(`${B}/${id}`, token);
    return claimDetailSchema.parse(raw);
  },
  create: (
    token: string,
    body: { order_id: string; claim_type: string; description?: string; priority?: string }
  ) => adminFetch<ClaimRow>(B, token, { method: "POST", body: JSON.stringify(body) }),
  updateStatus: (token: string, id: string, status: string) =>
    adminFetch<ClaimDetail>(`${B}/${id}/status`, token, {
      method: "POST",
      body: JSON.stringify({ status }),
    }),
  assign: (token: string, id: string, investigator_id: string) =>
    adminFetch<ClaimDetail>(`${B}/${id}/assign`, token, {
      method: "POST",
      body: JSON.stringify({ investigator_id }),
    }),
  autoAssign: (token: string, id: string) =>
    adminFetch<ClaimDetail>(`${B}/${id}/auto-assign`, token, { method: "POST" }),
  addEvidence: (
    token: string,
    id: string,
    body: { file_type: string; name: string; url?: string }
  ) =>
    adminFetch<ClaimDetail>(`${B}/${id}/evidence`, token, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  addNote: (token: string, id: string, body: string, internal = true) =>
    adminFetch<ClaimDetail>(`${B}/${id}/notes`, token, {
      method: "POST",
      body: JSON.stringify({ body, internal }),
    }),
  updateInvestigation: (token: string, id: string, investigation: Record<string, string>) =>
    adminFetch<ClaimDetail>(`${B}/${id}/investigation`, token, {
      method: "POST",
      body: JSON.stringify(investigation),
    }),
  setCompensation: (token: string, id: string, compensation: Record<string, number | string>) =>
    adminFetch<ClaimDetail>(`${B}/${id}/compensation`, token, {
      method: "POST",
      body: JSON.stringify(compensation),
    }),
  setInsurance: (token: string, id: string, insurance: Record<string, unknown>) =>
    adminFetch<ClaimDetail>(`${B}/${id}/insurance`, token, {
      method: "POST",
      body: JSON.stringify(insurance),
    }),
  bulk: (
    token: string,
    claimIds: string[],
    action: string,
    opts?: { investigator_id?: string; status?: string }
  ) =>
    adminFetch<{ results: Array<{ claim_id: string; status: string }> }>(`${B}/bulk`, token, {
      method: "POST",
      body: JSON.stringify({ claim_ids: claimIds, action, ...opts }),
    }),
};

export const STATUS_STYLES: Record<string, string> = {
  new: "bg-blue-100 text-blue-700",
  assigned: "bg-indigo-100 text-indigo-700",
  under_investigation: "bg-violet-100 text-violet-700",
  waiting_customer: "bg-amber-100 text-amber-700",
  waiting_merchant: "bg-amber-100 text-amber-700",
  waiting_driver: "bg-amber-100 text-amber-700",
  waiting_insurance: "bg-orange-100 text-orange-700",
  approved: "bg-green-100 text-green-700",
  rejected: "bg-red-100 text-red-700",
  compensated: "bg-teal-100 text-teal-800",
  closed: "bg-gray-100 text-gray-600",
  archived: "bg-gray-100 text-gray-500",
  open: "bg-blue-100 text-blue-700",
  investigating: "bg-violet-100 text-violet-700",
  resolved: "bg-green-100 text-green-700",
};

export const PRIORITY_STYLES: Record<string, string> = {
  low: "bg-gray-100 text-gray-600",
  normal: "bg-blue-50 text-blue-700",
  high: "bg-amber-100 text-amber-800",
  critical: "bg-red-100 text-red-700",
};

export function exportClaimsCsv(rows: ClaimRow[], filename = "claims.csv") {
  const headers = [
    "claim_number",
    "claim_type",
    "display_status",
    "priority",
    "merchant_name",
    "customer_email",
    "driver_name",
    "tracking_number",
    "amount_cents",
    "risk_score",
    "assigned_investigator",
    "created_at",
  ];
  const lines = [
    headers.join(","),
    ...rows.map((r) =>
      headers
        .map((h) => {
          const v = r[h as keyof ClaimRow];
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

export function formatClaimType(t: string) {
  return t.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}
