import { z } from "zod";
import { adminFetch } from "@/lib/api";

const summarySchema = z.object({
  monthly_orders: z.number(),
  monthly_revenue_cents: z.number(),
  active_merchants: z.number(),
  active_drivers: z.number(),
  delivery_sla_percent: z.number(),
  cancellation_rate_percent: z.number(),
  claim_rate_percent: z.number(),
});

export type ReportsSummary = z.infer<typeof summarySchema>;

export type ReportCategory = { id: string; label: string; module: string };

export type ReportsCenter = {
  summary: ReportsSummary;
  executive: Record<string, unknown>;
  operations: Record<string, unknown>;
  delivery_performance: Record<string, unknown>;
  trends: { labels: string[]; orders: number[]; revenue_cents: number[] };
  modules: Record<string, unknown>;
  smart: Record<string, unknown>;
  categories: ReportCategory[];
  role_dashboards: string[];
};

export type SavedReport = {
  id: string;
  name: string;
  category_id: string;
  chart_type: string;
  filters: Record<string, unknown>;
  pinned: boolean;
  favorite: boolean;
  created_at: string;
};

export type ScheduledReport = {
  id: string;
  name: string;
  category_id: string;
  schedule: string;
  email: string;
  active: boolean;
  created_at: string;
};

export type BuilderDataset = {
  id: string;
  label: string;
  fields: string[];
  group_by: string[];
  metrics: string[];
};

const B = "/v1/admin/reports";

export const REPORT_CATEGORIES: ReportCategory[] = [
  { id: "executive", label: "Executive", module: "center" },
  { id: "operations", label: "Operations", module: "orders" },
  { id: "orders", label: "Orders", module: "orders" },
  { id: "booking_drafts", label: "Booking Drafts", module: "booking" },
  { id: "finance", label: "Finance", module: "finance" },
  { id: "claims", label: "Claims", module: "claims" },
  { id: "support", label: "Support", module: "support" },
  { id: "crm", label: "CRM", module: "crm" },
  { id: "pricing", label: "Pricing", module: "pricing" },
  { id: "delivery", label: "Delivery Performance", module: "orders" },
  { id: "merchants", label: "Merchants", module: "orders" },
  { id: "drivers", label: "Drivers", module: "orders" },
];

export const reportsApi = {
  summary: async (token: string) => {
    const raw = await adminFetch<unknown>(`${B}/summary`, token);
    return summarySchema.parse(raw);
  },
  center: (token: string) => adminFetch<ReportsCenter>(`${B}/center`, token),
  executive: (token: string) => adminFetch<Record<string, unknown>>(`${B}/executive`, token),
  categories: (token: string) => adminFetch<ReportCategory[]>(`${B}/categories`, token),
  category: (token: string, id: string) =>
    adminFetch<Record<string, unknown>>(`${B}/category/${id}`, token),
  modules: (token: string) => adminFetch<Record<string, unknown>>(`${B}/modules`, token),
  trends: (token: string, months = 12) =>
    adminFetch<{ labels: string[]; orders: number[]; revenue_cents: number[] }>(
      `${B}/trends?months=${months}`,
      token
    ),
  deliveryPerformance: (token: string) =>
    adminFetch<Record<string, unknown>>(`${B}/delivery-performance`, token),
  smart: (token: string) => adminFetch<Record<string, unknown>>(`${B}/smart`, token),
  saved: (token: string) => adminFetch<SavedReport[]>(`${B}/saved`, token),
  saveReport: (
    token: string,
    body: { name: string; category_id: string; chart_type?: string; pinned?: boolean }
  ) =>
    adminFetch<SavedReport>(`${B}/saved`, token, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  deleteSaved: (token: string, id: string) =>
    adminFetch<{ status: string }>(`${B}/saved/${id}`, token, { method: "DELETE" }),
  scheduled: (token: string) => adminFetch<ScheduledReport[]>(`${B}/scheduled`, token),
  scheduleReport: (
    token: string,
    body: { name: string; category_id: string; schedule: string; email: string }
  ) =>
    adminFetch<ScheduledReport>(`${B}/scheduled`, token, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  builderDatasets: (token: string) => adminFetch<BuilderDataset[]>(`${B}/builder/datasets`, token),
  builderPreview: (token: string, body: { dataset: string; group_by: string; metric?: string }) =>
    adminFetch<{ series: Array<{ label: string; value: number; count: number }> }>(
      `${B}/builder/preview`,
      token,
      { method: "POST", body: JSON.stringify(body) }
    ),
  exportAudit: (token: string, reportId: string, format: string) =>
    adminFetch<{ status: string }>(`${B}/export-audit`, token, {
      method: "POST",
      body: JSON.stringify({ report_id: reportId, format }),
    }),
};

export function exportReportCsv(filename: string, headers: string[], rows: string[][]) {
  const lines = [
    headers.join(","),
    ...rows.map((r) => r.map((c) => (c.includes(",") ? `"${c}"` : c)).join(",")),
  ];
  const blob = new Blob([lines.join("\n")], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export function pairsToChartData(
  pairs: Array<[string, number]> | Array<{ label: string; value: number }>
) {
  if (!pairs.length) return { labels: [] as string[], values: [] as number[] };
  if (Array.isArray(pairs[0])) {
    const p = pairs as Array<[string, number]>;
    return { labels: p.map((x) => x[0]), values: p.map((x) => x[1]) };
  }
  const p = pairs as Array<{ label: string; value: number }>;
  return { labels: p.map((x) => x.label), values: p.map((x) => x.value) };
}

export function dictToPairs(d: Record<string, number> | undefined, limit = 10) {
  if (!d) return [] as Array<[string, number]>;
  return Object.entries(d)
    .sort((a, b) => b[1] - a[1])
    .slice(0, limit) as Array<[string, number]>;
}
