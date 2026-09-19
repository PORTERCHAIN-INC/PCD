import { publicEnv } from "@/lib/env";

const API_BASE = publicEnv.porterchainApiUrl;

export type ChartPoint = { label: string; value: number };

export type MonthlyTrends = {
  labels: string[];
  orders: number[];
  spend_cents: number[];
};

export type KpiItem = {
  label: string;
  value: number | null;
  format: "number" | "currency" | "percent";
};

export type ReportPeriod = {
  label: string;
  since: string;
  timezone: string;
  note: string;
};

export type SpendSlice = {
  channel: string;
  orders: number;
  spend_cents: number;
};

export type PricingModelSlice = {
  pricing_model: string;
  orders: number;
  spend_cents: number;
};

export type PricingBandSlice = {
  band: string;
  pricing_model: string;
  orders: number;
  spend_cents: number;
};

export type ExecutiveReport = {
  monthly_orders: number;
  monthly_spend_cents: number;
  growth_percent: number;
  orders_in_progress: number;
  delivered_today: number;
  failed_deliveries: number;
  open_claims: number;
  on_time_percent: number | null;
  delivery_success_percent: number | null;
  sla_percent: number | null;
  avg_delivery_hours: number | null;
  avg_pickup_hours: number | null;
  period?: ReportPeriod;
  invoice_summary_cents: number;
  top_routes: Array<{ route: string; count: number }>;
  top_destinations: Array<{ destination: string; count: number }>;
  spend_by_channel?: SpendSlice[];
  spend_by_pricing_model?: PricingModelSlice[];
  top_pricing_bands?: PricingBandSlice[];
  charts: {
    monthly_trends: MonthlyTrends;
    daily_orders: ChartPoint[];
    daily_spend_cents: ChartPoint[];
  };
  kpis: KpiItem[];
};

export type DeliveryPerformance = {
  total_orders: number;
  delivered: number;
  failed_deliveries: number;
  returned: number;
  on_time_percent: number | null;
  on_time_orders?: number;
  on_time_sample_size?: number;
  grace_minutes?: number;
  delivery_success_percent: number | null;
  failed_percent: number | null;
  sla_percent: number | null;
  avg_pickup_hours: number | null;
  avg_delivery_hours: number | null;
  period?: ReportPeriod;
};

export type DriverRow = {
  driver_id: string;
  name: string;
  orders: number;
  delivered: number;
  failed: number;
  success_percent: number;
};

export type VehicleRow = {
  vehicle_id: string;
  label: string;
  vehicle_class: string | null;
  orders: number;
};

export type ClaimsSummary = {
  total_claims: number;
  open_claims: number;
  by_type: Record<string, number>;
  by_status: Record<string, number>;
  compensation_cost_cents: number;
};

export type InvoiceReport = {
  invoice_count: number;
  invoice_total_cents: number;
  tax_cents: number;
  currency: string;
  invoices: Array<Record<string, unknown>>;
  spend_by_channel?: SpendSlice[];
  spend_by_pricing_model?: PricingModelSlice[];
  top_pricing_bands?: PricingBandSlice[];
  period?: ReportPeriod;
};

export type SavedReport = {
  id: string;
  name: string;
  report_type: string;
  chart_type: string;
  filters: Record<string, unknown>;
  created_at: string;
  created_by: string;
};

export type ScheduledReport = {
  id: string;
  name: string;
  report_type: string;
  schedule: string;
  email: string;
  active: boolean;
  created_at: string;
};

export type ReportsOverview = {
  executive: ExecutiveReport;
  delivery_performance: DeliveryPerformance;
  order_volume: {
    monthly_trends: MonthlyTrends;
    daily_orders: ChartPoint[];
    daily_spend_cents: ChartPoint[];
    top_routes: Array<{ route: string; count: number }>;
  };
  invoice_reports: InvoiceReport;
  driver_performance: { drivers: DriverRow[] };
  vehicle_usage: { vehicles: VehicleRow[] };
  top_destinations: { destinations: Array<{ destination: string; count: number }> };
  claims_summary: ClaimsSummary;
  saved_reports: SavedReport[];
  scheduled_reports: ScheduledReport[];
  scheduled_email_available?: boolean;
  period?: ReportPeriod;
};

function reportHeaders(token: string, orgId?: string, body?: BodyInit): Record<string, string> {
  const headers: Record<string, string> = {
    Authorization: `Bearer ${token}`,
  };
  if (orgId) headers["X-Merchant-Id"] = orgId;
  if (body && !(body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }
  return headers;
}

async function reportsFetch<T>(
  path: string,
  token: string,
  init?: RequestInit & { orgId?: string }
): Promise<T> {
  const { orgId, ...rest } = init ?? {};
  const response = await fetch(`${API_BASE}${path}`, {
    ...rest,
    headers: {
      ...reportHeaders(token, orgId, rest.body ?? undefined),
      ...(rest.headers as Record<string, string>),
    },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const detail = body.detail;
    const message =
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? detail.map((d: { msg?: string }) => d.msg || JSON.stringify(d)).join("; ")
          : `API error ${response.status}`;
    throw new Error(message);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

async function reportsDownload(
  path: string,
  token: string,
  orgId?: string,
  filename = "report.csv"
) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: reportHeaders(token, orgId),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const detail =
      typeof body.detail === "string" ? body.detail : "Could not download that report.";
    throw new Error(detail);
  }
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export const reportsApi = {
  overview: (token: string, orgId?: string) =>
    reportsFetch<ReportsOverview>("/v1/merchant/reports/overview", token, { orgId }),

  executive: (token: string, orgId?: string) =>
    reportsFetch<ExecutiveReport>("/v1/merchant/reports/executive", token, { orgId }),

  deliveryPerformance: (token: string, orgId?: string) =>
    reportsFetch<DeliveryPerformance>("/v1/merchant/reports/delivery-performance", token, {
      orgId,
    }),

  saved: (token: string, orgId?: string) =>
    reportsFetch<SavedReport[]>("/v1/merchant/reports/saved", token, { orgId }),

  saveReport: (
    token: string,
    body: { name: string; report_type: string; chart_type?: string },
    orgId?: string
  ) =>
    reportsFetch<SavedReport>("/v1/merchant/reports/saved", token, {
      method: "POST",
      body: JSON.stringify(body),
      orgId,
    }),

  deleteSaved: (token: string, reportId: string, orgId?: string) =>
    reportsFetch<{ ok: boolean }>(`/v1/merchant/reports/saved/${reportId}`, token, {
      method: "DELETE",
      orgId,
    }),

  scheduled: (token: string, orgId?: string) =>
    reportsFetch<ScheduledReport[]>("/v1/merchant/reports/scheduled", token, { orgId }),

  scheduleReport: (
    token: string,
    body: { name: string; report_type: string; schedule: string; email: string },
    orgId?: string
  ) =>
    reportsFetch<ScheduledReport>("/v1/merchant/reports/scheduled", token, {
      method: "POST",
      body: JSON.stringify(body),
      orgId,
    }),

  exportCsv: (token: string, reportType: string, orgId?: string) =>
    reportsDownload(
      `/v1/merchant/reports/export/${reportType}.csv`,
      token,
      orgId,
      `merchant-${reportType}-report.csv`
    ),

  exportExcel: (token: string, reportType: string, orgId?: string) =>
    reportsDownload(
      `/v1/merchant/reports/export/${reportType}.xlsx`,
      token,
      orgId,
      `merchant-${reportType}-report.xlsx`
    ),
};

export function formatPercent(value: number | null | undefined): string {
  return value == null ? "—" : `${value}%`;
}

export const REPORT_TYPES = [
  { id: "executive", label: "Overview" },
  { id: "delivery", label: "Delivery performance" },
  { id: "invoices", label: "Invoices" },
  { id: "destinations", label: "Top destinations" },
  { id: "claims", label: "Claims" },
] as const;
