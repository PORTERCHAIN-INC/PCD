/**
 * Shared health status mapper + Zod contracts (mirrors API platform/health_status.py).
 * Health-dashboard triad: healthy | warning | critical (Jeff Dean phase_1).
 * Compact UI may also surface "unknown" when a key is missing.
 */

import { z } from "zod";

export type HealthTriad = "healthy" | "warning" | "critical";
export type HealthStatus = HealthTriad | "unknown";

const HEALTHY_EXACT = new Set([
  "healthy",
  "ok",
  "pass",
  "configured",
  "bridge_enabled",
  "enabled",
  "ready",
  "local",
  "operational",
  "legacy_ok",
]);

const WARNING_EXACT = new Set([
  "warning",
  "degraded",
  "mock",
  "mock_or_unconfigured",
  "bypass",
  "dev_bypass",
  "disabled",
  "bridge_disabled",
  "unconfigured",
  "not_configured",
  "unavailable",
  "log_only",
  "dry_run",
  "push_disabled",
  "sdk_missing",
  "no_heartbeat",
  "skipped",
  "shadow",
  "unknown",
]);

const WARNING_SUBSTRINGS = [
  "warning",
  "degraded",
  "mock",
  "bypass",
  "disabled",
  "unconfigured",
  "unavailable",
  "below_slo",
  "missing_secret",
  "dry_run",
  "legacy",
] as const;

const CRITICAL_SUBSTRINGS = ["error", "critical", "unreachable", "unbonded", "fail"] as const;

/** Map a readiness/integration probe token to the Jeff Dean triad. */
export function normalizeCheckStatus(raw: string | null | undefined): HealthTriad {
  if (raw == null) return "warning";
  const s = String(raw).trim().toLowerCase();
  if (!s) return "warning";
  if (HEALTHY_EXACT.has(s)) return "healthy";
  if (WARNING_EXACT.has(s)) return "warning";
  if (CRITICAL_SUBSTRINGS.some((x) => s.includes(x))) return "critical";
  if (WARNING_SUBSTRINGS.some((x) => s.includes(x))) return "warning";
  return "warning";
}

/**
 * Resolve status from a string or `{ status }` object.
 * Missing / empty → ``unknown`` (compact UI only — never emit on health-dashboard components).
 */
export function healthStatus(value: unknown): HealthStatus {
  if (value == null) return "unknown";
  if (typeof value === "object" && value !== null && "status" in value) {
    const raw = (value as { status: unknown }).status;
    if (raw == null || raw === "") return "unknown";
    return normalizeCheckStatus(String(raw));
  }
  if (typeof value === "string") {
    if (!value.trim()) return "unknown";
    return normalizeCheckStatus(value);
  }
  return "unknown";
}

export const healthTriadSchema = z.enum(["healthy", "warning", "critical"]);

export const integrationComponentSchema = z
  .object({
    status: healthTriadSchema,
    raw: z.string().nullable().optional(),
  })
  .passthrough();

export const integrationHealthSchema = z
  .object({
    api: integrationComponentSchema,
    database: integrationComponentSchema,
    redis: integrationComponentSchema,
  })
  .passthrough();

export type IntegrationHealth = z.infer<typeof integrationHealthSchema>;

export const healthComponentSchema = z
  .object({
    id: z.string(),
    name: z.string(),
    category: z.string(),
    status: healthTriadSchema,
    latency_ms: z.number().nullable().optional(),
    last_sync: z.string().nullable().optional(),
    version: z.string().nullable().optional(),
    errors: z.array(z.string()).optional(),
    warnings: z.array(z.string()).optional(),
    recovery_status: z.string().optional(),
    details: z.record(z.string(), z.unknown()).optional(),
  })
  .passthrough();

export const healthDashboardSchema = z
  .object({
    overall: healthTriadSchema,
    checked_at: z.string(),
    version: z.string(),
    environment: z.string(),
    summary: z.object({
      healthy: z.number(),
      warning: z.number(),
      critical: z.number(),
    }),
    components: z.array(healthComponentSchema),
    groups: z.record(z.string(), z.unknown()).optional(),
    masterrule_compliance: z.unknown().optional(),
  })
  .passthrough();

export type HealthDashboardParsed = z.infer<typeof healthDashboardSchema>;

/** Human labels for compact integration_health keys. */
export const INTEGRATION_HEALTH_LABELS: Record<string, string> = {
  api: "API",
  database: "Database",
  redis: "Redis",
  queue: "Queue",
  stripe: "Stripe",
  fleetbase: "Fleetbase",
  google_maps: "Google Maps",
  firebase: "Firebase",
  clerk: "Clerk",
  storage: "Storage",
  email: "Email",
  sms: "SMS",
  push: "Push",
  nvidia_nim: "NVIDIA NIM",
  nvidia_cuopt: "NVIDIA cuOpt",
};

export const INTEGRATION_HEALTH_CORE_KEYS = [
  "api",
  "database",
  "redis",
  "stripe",
  "fleetbase",
  "google_maps",
  "firebase",
  "clerk",
  "email",
  "storage",
] as const;
