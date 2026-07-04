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
  value: number;
  format: "number" | "currency" | "percent";
};

export type ExecutiveReport = {
  monthly_orders: number;
  monthly_spend_cents: number;
  growth_percent: number;
  orders_in_progress: number;
  delivered_today: number;
  failed_deliveries: number;
  open_claims: number;
  on_time_percent: number;
  delivery_success_percent: number;
  sla_percent: number;
  avg_delivery_hours: number;
  avg_pickup_hours: number;
  invoice_summary_cents: number;
  top_routes: Array<{ route: string; count: number }>;
  top_destinations: Array<{ destination: string; count: number }>;
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
  on_time_percent: number;
  delivery_success_percent: number;
  failed_percent: number;
  sla_percent: number;
  avg_pickup_hours: number;
  avg_delivery_hours: number;
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
};

async function reportsFetch<T>(
  path: string,
  token: string,
  init?: RequestInit & { orgId?: string }
): Promise<T> {
  const headers: Record<string, string> = {
    Authorization: `Bearer ${token}`,
  };
  if (init?.body && !(init.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { ...headers, ...(init?.headers as Record<string, string>) },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `API error ${response.status}`);
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
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  if (!response.ok) throw new Error("Download failed");
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
    reportsFetch<DeliveryPerformance>("/v1/merchant/reports/delivery-performance", token, { orgId }),

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

export const REPORT_TYPES = [
  { id: "executive", label: "Executive dashboard" },
  { id: "delivery", label: "Delivery performance" },
  { id: "orders", label: "Order volume" },
  { id: "invoices", label: "Invoice reports" },
  { id: "drivers", label: "Driver performance" },
  { id: "vehicles", label: "Vehicle usage" },
  { id: "destinations", label: "Top destinations" },
  { id: "claims", label: "Claims summary" },
] as const;
