import { adminFetch } from "@/lib/api";
import { healthStatus, integrationHealthSchema, type IntegrationHealth } from "@/lib/health";

export type DashboardCenter = {
  meta: {
    generated_at: string;
    environment: string;
    version: string;
    company: string;
    role: string;
  };
  kpis: Record<string, number | unknown>;
  operations: Record<string, unknown>;
  orders: Record<string, number>;
  finance: Record<string, unknown>;
  claims: Record<string, number>;
  support: Record<string, unknown>;
  crm: Record<string, unknown>;
  booking: Record<string, unknown>;
  merchants: Record<string, unknown>;
  customers: Record<string, unknown>;
  drivers: Record<string, unknown>;
  fleet: Record<string, unknown>;
  trends: { labels: string[]; orders: number[]; revenue_cents: number[] };
  executive: Record<string, unknown>;
  activity: Array<{
    id: string;
    event_type: string;
    aggregate_type: string;
    aggregate_id: string;
    actor_type: string;
    occurred_at: string | null;
  }>;
  system_health: IntegrationHealth | Record<string, unknown>;
  smart: Record<string, unknown>;
  pending: Record<string, number>;
  quick_actions: Array<{ id: string; label: string; href: string }>;
};

export type SearchHit = {
  type: string;
  id: string;
  label: string;
  subtitle?: string;
  href?: string;
};

const B = "/v1/admin/dashboard";

export const dashboardApi = {
  legacy: (token: string) => adminFetch<Record<string, unknown>>("/v1/admin/dashboard", token),
  center: async (token: string) => {
    const raw = await adminFetch<DashboardCenter>(`${B}/center`, token);
    const parsed = integrationHealthSchema.safeParse(raw.system_health);
    if (parsed.success) {
      return { ...raw, system_health: parsed.data };
    }
    return raw;
  },
  search: (token: string, q: string) =>
    adminFetch<SearchHit[]>(`${B}/search?q=${encodeURIComponent(q)}`, token),
};

export const DASHBOARD_WIDGETS = [
  { id: "kpis", label: "Executive KPIs", defaultVisible: true },
  { id: "operations", label: "Operations Center", defaultVisible: true },
  { id: "orders", label: "Orders", defaultVisible: true },
  { id: "booking", label: "Booking", defaultVisible: true },
  { id: "finance", label: "Finance", defaultVisible: true },
  { id: "support", label: "Support", defaultVisible: true },
  { id: "claims", label: "Claims", defaultVisible: true },
  { id: "crm", label: "CRM", defaultVisible: true },
  { id: "merchants", label: "Merchants", defaultVisible: true },
  { id: "drivers", label: "Drivers", defaultVisible: true },
  { id: "fleet", label: "Fleet", defaultVisible: true },
  { id: "reports", label: "Reports", defaultVisible: true },
  { id: "activity", label: "Activity Timeline", defaultVisible: true },
  { id: "health", label: "Health", defaultVisible: true },
  { id: "smart", label: "Smart Insights", defaultVisible: true },
  { id: "sidebar", label: "Right Sidebar", defaultVisible: true },
] as const;

export type WidgetId = (typeof DASHBOARD_WIDGETS)[number]["id"];

const LAYOUT_KEY = "porterchain-dashboard-layout";

export function loadWidgetLayout(): Record<WidgetId, boolean> {
  if (typeof window === "undefined") {
    return Object.fromEntries(DASHBOARD_WIDGETS.map((w) => [w.id, w.defaultVisible])) as Record<
      WidgetId,
      boolean
    >;
  }
  try {
    const raw = localStorage.getItem(LAYOUT_KEY);
    if (!raw) throw new Error("empty");
    return JSON.parse(raw) as Record<WidgetId, boolean>;
  } catch {
    return Object.fromEntries(DASHBOARD_WIDGETS.map((w) => [w.id, w.defaultVisible])) as Record<
      WidgetId,
      boolean
    >;
  }
}

export function saveWidgetLayout(layout: Record<WidgetId, boolean>) {
  localStorage.setItem(LAYOUT_KEY, JSON.stringify(layout));
}

export { healthStatus };
