import { adminFetch } from "@/lib/api";

export type HealthComponent = {
  id: string;
  name: string;
  category: string;
  status: "healthy" | "warning" | "critical";
  latency_ms: number | null;
  last_sync: string | null;
  version: string | null;
  errors: string[];
  warnings: string[];
  recovery_status: string;
  details: Record<string, unknown>;
};

export type HealthGroup = {
  label: string;
  items: HealthComponent[];
  summary: { healthy: number; warning: number; critical: number };
};

export type MasterruleCheck = {
  id: string;
  label: string;
  status: string;
  note: string;
};

export type HealthDashboard = {
  overall: string;
  checked_at: string;
  version: string;
  environment: string;
  summary: { healthy: number; warning: number; critical: number };
  components: HealthComponent[];
  groups: Record<string, HealthGroup>;
  masterrule_compliance: { overall: string; checks: MasterruleCheck[] };
  /** Process-local staff auth SLI counters (ok / fail / required). */
  auth_sli?: Record<string, Record<string, number>>;
  auth_posture?: {
    cookie_domain_mode: string;
    auth_bypass_allowed: boolean;
    cookie_secure: boolean;
    cookie_samesite: string;
    cookie_domain: string | null;
    staff_idp: string;
  };
};

export type AiUsageRow = {
  id: string;
  provider: string;
  model: string;
  feature: string;
  status: string;
  total_tokens: number;
  latency_ms: number | null;
  error: string | null;
  created_at: string | null;
};

export type AiUsageFeatureAgg = {
  feature: string;
  provider: string;
  calls: number;
  total_tokens: number;
  prompt_tokens: number;
  completion_tokens: number;
  errors: number;
};

export type AiUsageDashboard = {
  checked_at: string;
  window: string;
  nim: {
    configured: boolean;
    provider: string;
    model: string;
    api_base: string;
    circuit_open: boolean;
    fail_streak: number;
  };
  phase2: { intelligence: boolean; ai_dispatch: boolean };
  by_feature: AiUsageFeatureAgg[];
  recent: AiUsageRow[];
};

export type TestCatalogItem = {
  id: string;
  name: string;
  category: string;
  description: string;
  masterrule: string;
};

export type TestResult = {
  id: string;
  name: string;
  category?: string;
  description?: string;
  masterrule?: string;
  status: "healthy" | "warning" | "critical";
  execution_ms: number;
  logs: string[];
  details: Record<string, unknown>;
  ran_at: string;
};

export type PlatformValidation = {
  summary: { pass: number; warning: number; fail: number };
  execution_ms: number;
  results: TestResult[];
  groups: Record<string, TestResult[]>;
  ran_at: string;
};

export const HEALTH_CATEGORY_ORDER = [
  "portals",
  "engines",
  "integrations",
  "infrastructure",
  "observability",
] as const;

export const HEALTH_CATEGORY_LABELS: Record<string, string> = {
  portals: "Applications & Portals",
  engines: "Application Engines",
  integrations: "External Integrations",
  infrastructure: "Infrastructure",
  observability: "Observability & Workers",
};

export const TEST_CATEGORY_LABELS: Record<string, string> = {
  integrations: "Integrations",
  infrastructure: "Infrastructure",
  engines: "Engines",
  observability: "Observability",
};

export const E2E_REPORT_FILES = [
  "SYSTEM_VALIDATION_REPORT.md",
  "FORWARD_LOGISTICS_REPORT.md",
  "REVERSE_LOGISTICS_REPORT.md",
  "FAILURE_SCENARIOS_REPORT.md",
  "EVENT_BUS_REPORT.md",
  "NOTIFICATION_REPORT.md",
  "FLEETBASE_SYNC_REPORT.md",
  "DATA_CONSISTENCY_REPORT.md",
  "API_TRACE_REPORT.md",
  "PRODUCTION_READINESS_REPORT.md",
] as const;

export type E2EResult = {
  overall: string;
  production_ready: boolean;
  summary: { pass: number; warning: number; fails: number; blockers: number; total: number };
  phases: Record<string, unknown>;
  reports: Record<string, string>;
  written_files: string[];
  execution_ms: number;
  ran_at: string;
};

const B = "/v1/admin/diagnostics";

export const diagnosticsApi = {
  center: (token: string) =>
    adminFetch<Record<string, unknown>>(`${B}/center`, token, { timeoutMs: 45_000 }),

  health: (token: string) =>
    adminFetch<HealthDashboard>(`${B}/health`, token, { timeoutMs: 45_000 }),

  listTests: (token: string) =>
    adminFetch<{ tests: TestCatalogItem[]; count: number }>(`${B}/tests`, token),

  runTest: (token: string, testId: string) =>
    adminFetch<TestResult>(`${B}/tests/${testId}`, token, { method: "POST", timeoutMs: 90_000 }),

  runAllTests: (token: string) =>
    adminFetch<PlatformValidation>(`${B}/tests/run`, token, { method: "POST", timeoutMs: 180_000 }),

  architecture: (token: string) =>
    adminFetch<Record<string, unknown>>(`${B}/architecture`, token, { timeoutMs: 45_000 }),

  modules: (token: string) =>
    adminFetch<Record<string, unknown>>(`${B}/modules`, token, { timeoutMs: 45_000 }),

  workflows: (token: string) =>
    adminFetch<Record<string, unknown>>(`${B}/workflows`, token, { timeoutMs: 45_000 }),

  simulateWorkflow: (token: string, scenarioId: string) =>
    adminFetch<Record<string, unknown>>(`${B}/workflows/${scenarioId}/simulate`, token, {
      method: "POST",
      timeoutMs: 45_000,
    }),

  events: (token: string, filter?: string) => {
    const q = filter ? `?filter=${encodeURIComponent(filter)}` : "";
    return adminFetch<Record<string, unknown>>(`${B}/events${q}`, token);
  },

  fleetbaseSync: (token: string) =>
    adminFetch<Record<string, unknown>>(`${B}/fleetbase-sync`, token),

  aiUsage: (token: string, limit = 40) =>
    adminFetch<AiUsageDashboard>(`${B}/ai-usage?limit=${limit}`, token),

  chaos: (token: string, scenario: string) =>
    adminFetch<Record<string, unknown>>(`${B}/chaos/${scenario}`, token, {
      method: "POST",
      timeoutMs: 90_000,
    }),

  observability: (token: string) =>
    adminFetch<Record<string, unknown>>(`${B}/observability`, token, { timeoutMs: 45_000 }),

  generateReports: (token: string, writeFiles = false) =>
    adminFetch<{ reports: Record<string, string>; written_files: string[] }>(
      `${B}/reports/generate`,
      token,
      { method: "POST", body: JSON.stringify({ write_files: writeFiles }), timeoutMs: 300_000 }
    ),

  runE2E: (
    token: string,
    opts?: { writeFiles?: boolean; cleanup?: boolean; merchantOrderCount?: number }
  ) =>
    adminFetch<E2EResult>(`${B}/e2e/run`, token, {
      method: "POST",
      body: JSON.stringify({
        write_files: opts?.writeFiles ?? false,
        cleanup: opts?.cleanup ?? true,
        merchant_order_count: opts?.merchantOrderCount ?? 100,
      }),
      timeoutMs: 600_000,
    }),

  e2ePhases: (token: string) =>
    adminFetch<{ phases: Array<Record<string, unknown>> }>(`${B}/e2e/phases`, token),
};

export const CHAOS_SCENARIOS = [
  "fleetbase_offline",
  "stripe_offline",
  "clerk_offline",
  "firebase_offline",
  "google_maps_failure",
  "osrm_failure",
  "valhalla_failure",
  "redis_restart",
  "postgresql_restart",
  "websocket_failure",
  "driver_reject",
  "vehicle_breakdown",
  "gps_loss",
  "webhook_delay",
] as const;

export function statusTone(status: string): "green" | "amber" | "red" | "gray" {
  const s = status.toLowerCase();
  if (s === "healthy" || s === "pass" || s === "ok") return "green";
  if (s === "warning" || s === "degraded") return "amber";
  if (s === "critical" || s === "fail") return "red";
  return "gray";
}

export function statusIcon(status: string): string {
  const tone = statusTone(status);
  if (tone === "green") return "✅";
  if (tone === "amber") return "⚠";
  if (tone === "red") return "❌";
  return "○";
}

export function downloadReport(filename: string, content: string) {
  const blob = new Blob([content], { type: "text/markdown" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export function filterComponents(
  components: HealthComponent[],
  query: string,
  category: string | null,
  statusFilter: string | null
) {
  const q = query.trim().toLowerCase();
  return components.filter((c) => {
    if (category && c.category !== category) return false;
    if (statusFilter && c.status !== statusFilter) return false;
    if (!q) return true;
    return (
      c.name.toLowerCase().includes(q) ||
      c.id.toLowerCase().includes(q) ||
      c.errors.some((e) => e.toLowerCase().includes(q)) ||
      c.warnings.some((w) => w.toLowerCase().includes(q))
    );
  });
}
