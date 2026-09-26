import { z } from "zod";
import { adminFetch } from "@/lib/api";
import { healthStatus, integrationHealthSchema, type IntegrationHealth } from "@/lib/health";

const trendsSchema = z.object({
  labels: z.array(z.string()),
  orders: z.array(z.number()),
  revenue_cents: z.array(z.number()),
});

const dashboardCenterSchema = z
  .object({
    meta: z.object({
      generated_at: z.string(),
      environment: z.string(),
      version: z.string(),
      company: z.string(),
      role: z.string(),
    }),
    kpis: z.record(z.string(), z.unknown()),
    operations: z.record(z.string(), z.unknown()),
    orders: z.record(z.string(), z.unknown()),
    finance: z.record(z.string(), z.unknown()),
    claims: z.record(z.string(), z.unknown()),
    support: z.record(z.string(), z.unknown()),
    crm: z.record(z.string(), z.unknown()),
    booking: z.record(z.string(), z.unknown()),
    merchants: z.record(z.string(), z.unknown()),
    customers: z.record(z.string(), z.unknown()),
    drivers: z.record(z.string(), z.unknown()),
    fleet: z.record(z.string(), z.unknown()),
    trends: trendsSchema,
    executive: z.record(z.string(), z.unknown()),
    activity: z.array(
      z.object({
        id: z.string(),
        event_type: z.string(),
        aggregate_type: z.string(),
        aggregate_id: z.string().nullable().optional().default(""),
        actor_type: z.string().optional().default("system"),
        occurred_at: z.string().nullable(),
      })
    ),
    system_health: z.record(z.string(), z.unknown()),
    smart: z.record(z.string(), z.unknown()),
    pending: z.record(z.string(), z.unknown()),
    quick_actions: z.array(
      z.object({
        id: z.string(),
        label: z.string(),
        href: z.string(),
      })
    ),
  })
  .passthrough();

export type DashboardCenter = z.infer<typeof dashboardCenterSchema> & {
  system_health: IntegrationHealth | Record<string, unknown>;
  pending: Record<string, number>;
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
    const parsed = dashboardCenterSchema.safeParse(raw);
    const base = parsed.success ? parsed.data : raw;
    const health = integrationHealthSchema.safeParse(base.system_health);
    return {
      ...base,
      system_health: health.success ? health.data : base.system_health,
      pending: Object.fromEntries(
        Object.entries(base.pending ?? {}).map(([k, v]) => [k, Number(v) || 0])
      ),
    } as DashboardCenter;
  },
  search: (token: string, q: string) =>
    adminFetch<SearchHit[]>(`${B}/search?q=${encodeURIComponent(q)}`, token),
};

export const DASHBOARD_WIDGETS = [
  { id: "kpis", label: "Executive KPIs", defaultVisible: true },
  { id: "smart", label: "Intelligence canvas", defaultVisible: true },
  { id: "operations", label: "Operations Center", defaultVisible: false },
  { id: "orders", label: "Orders", defaultVisible: false },
  { id: "booking", label: "Booking", defaultVisible: true },
  { id: "finance", label: "Finance", defaultVisible: true },
  { id: "support", label: "Support", defaultVisible: true },
  { id: "claims", label: "Claims", defaultVisible: true },
  { id: "crm", label: "CRM", defaultVisible: false },
  { id: "merchants", label: "Merchants", defaultVisible: true },
  { id: "drivers", label: "Drivers", defaultVisible: true },
  { id: "fleet", label: "Fleet", defaultVisible: true },
  { id: "reports", label: "Reports", defaultVisible: true },
  { id: "activity", label: "Activity Timeline", defaultVisible: true },
  { id: "health", label: "Health", defaultVisible: true },
  { id: "sidebar", label: "Right Sidebar", defaultVisible: true },
] as const;

export type WidgetId = (typeof DASHBOARD_WIDGETS)[number]["id"];

const LAYOUT_KEY = "porterchain-dashboard-layout-v2";

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
    const parsed = JSON.parse(raw) as Partial<Record<WidgetId, boolean>>;
    return Object.fromEntries(
      DASHBOARD_WIDGETS.map((w) => [w.id, parsed[w.id] ?? w.defaultVisible])
    ) as Record<WidgetId, boolean>;
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
