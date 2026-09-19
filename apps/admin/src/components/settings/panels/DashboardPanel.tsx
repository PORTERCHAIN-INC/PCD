"use client";

import { motion } from "framer-motion";
import { Activity, Clock, Database, Globe, Mail, Server, Shield } from "lucide-react";
import { relativeTime } from "@/lib/crmFormat";
import type { SettingsDashboard } from "@/lib/settings";
import { SettingsCard, SettingsPageHeader, StatTile, StatusPill } from "../ui/SettingsPrimitives";

function healthStatus(val: unknown): string {
  if (val == null) return "unknown";
  if (typeof val === "string") return val;
  if (typeof val === "object" && val !== null && "status" in val)
    return String((val as { status: unknown }).status);
  return String(val);
}

const INTEGRATION_META: Record<string, { label: string; note: string }> = {
  database: { label: "PostgreSQL", note: "Primary transactional store" },
  redis: { label: "Redis / Queue", note: "Event bus and job queue" },
  stripe: { label: "Stripe", note: "Payments — masterrule §14" },
  fleetbase: { label: "Fleetbase", note: "Execution engine via adapter only" },
  google_maps: { label: "Google Maps", note: "Places autocomplete & map tiles only" },
  firebase: { label: "Firebase", note: "Push notifications" },
  clerk: { label: "Clerk", note: "Identity — auth only, not RBAC" },
  nvidia_nim: {
    label: "NVIDIA NIM",
    note: "Read-only language assist — phase2 env flags",
  },
  email: { label: "Email (SMTP)", note: "Transactional delivery" },
  sms: { label: "SMS", note: "Clerk handles phone verification" },
  push: { label: "Push", note: "Driver & customer mobile" },
  storage: { label: "Storage", note: "Documents and media" },
  api: { label: "API", note: "Porterchain orchestrator" },
};

export default function DashboardPanel({
  dash,
  validation,
}: {
  dash: SettingsDashboard;
  validation?: { valid: boolean; issues: string[]; warnings: string[]; commercial_ok?: boolean };
}) {
  const health = dash.health as Record<string, unknown>;
  const integrations = Object.entries(INTEGRATION_META).filter(([k]) => k in health);

  return (
    <div className="space-y-6">
      <SettingsPageHeader
        title="Settings overview"
        description="Connection health and commercial readiness. Credentials are never displayed."
      />

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <StatTile
          label="System status"
          value={<StatusPill status={dash.system_status} />}
          tone={dash.system_status === "healthy" ? "success" : "warning"}
        />
        <StatTile label="Version" value={dash.version} sub="masterrule v3.1" />
        <StatTile
          label="Project mode"
          value={dash.project_mode?.mode ?? dash.environment}
          sub={`APP_ENV=${dash.environment}`}
          tone={
            dash.project_mode?.mode === "production"
              ? "warning"
              : dash.project_mode?.mode === "testing"
                ? "default"
                : "success"
          }
        />
        <StatTile
          label="Commercial"
          value={
            validation == null
              ? "—"
              : validation.commercial_ok !== false && validation.valid
                ? "Ready"
                : "Needs attention"
          }
          tone={validation?.valid && validation.commercial_ok !== false ? "success" : "warning"}
          sub={
            validation
              ? `${validation.issues.length} issues · ${validation.warnings.length} warnings`
              : undefined
          }
        />
      </div>

      {dash.project_mode ? (
        <SettingsCard
          title="Project mode (boot-time)"
          description="Deploy property — change APP_ENV in Doppler or env/.env, then restart. This process cannot switch itself."
        >
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <div>
              <p className="text-xs text-muted">Mode</p>
              <p className="font-mono font-semibold capitalize">{dash.project_mode.mode}</p>
            </div>
            <div>
              <p className="text-xs text-muted">Auth bypass</p>
              <p className="font-mono font-semibold">
                {dash.project_mode.auth_bypass_allowed ? "allowed" : "blocked"}
              </p>
            </div>
            <div>
              <p className="text-xs text-muted">Stripe mock</p>
              <p className="font-mono font-semibold">
                {dash.project_mode.stripe_mock_allowed ? "allowed" : "blocked"}
              </p>
            </div>
            <div>
              <p className="text-xs text-muted">Live Clerk</p>
              <p className="font-mono font-semibold">
                {dash.project_mode.requires_live_clerk ? "required" : "optional"}
              </p>
            </div>
          </div>
          <p className="mt-3 text-sm text-muted">
            {dash.project_mode.change_control} Local helper:{" "}
            <code className="rounded bg-muted/40 px-1 py-0.5 text-xs">
              pnpm mode:set development|testing|production
            </code>
          </p>
        </SettingsCard>
      ) : null}

      <SettingsCard
        title="Integration health"
        description="Adapter and infrastructure status — secrets in env only"
      >
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {integrations.map(([key, meta]) => {
            const raw = health[key];
            const status = healthStatus(raw);
            const extra =
              typeof raw === "object" && raw !== null
                ? Object.entries(raw as Record<string, unknown>)
                    .filter(([k]) => k !== "status")
                    .slice(0, key === "nvidia_nim" ? 4 : 2)
                    .map(([k, v]) => `${k}: ${v}`)
                    .join(" · ")
                : undefined;
            return (
              <motion.div
                key={key}
                initial={{ opacity: 0, y: 4 }}
                animate={{ opacity: 1, y: 0 }}
                className="rounded-xl border border-primary/10 bg-gray-bg/30 p-4"
              >
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <p className="text-sm font-semibold text-primary">{meta.label}</p>
                    <p className="mt-0.5 text-xs text-muted">{meta.note}</p>
                  </div>
                  <StatusPill status={status} />
                </div>
                {extra && <p className="mt-2 truncate text-[10px] font-mono text-muted">{extra}</p>}
              </motion.div>
            );
          })}
        </div>
      </SettingsCard>

      <SettingsCard
        title="Recent configuration changes"
        description="Audit trail for settings updates — full history in Audit section"
      >
        <ul className="divide-y divide-primary/5">
          {(dash.recent_changes as Array<Record<string, unknown>>).map((c, i) => (
            <li key={i} className="flex items-center justify-between gap-4 py-3 text-sm">
              <div className="flex items-center gap-2">
                <Activity className="h-4 w-4 text-secondary" />
                <span className="font-medium text-primary">{String(c.action ?? "update")}</span>
              </div>
              <span className="flex items-center gap-1 text-xs text-muted">
                <Clock className="h-3.5 w-3.5" />
                {c.created_at ? relativeTime(String(c.created_at)) : "—"}
              </span>
            </li>
          ))}
          {!dash.recent_changes.length && (
            <li className="py-8 text-center text-sm text-muted">
              No configuration changes recorded yet
            </li>
          )}
        </ul>
      </SettingsCard>

      <div className="grid gap-3 sm:grid-cols-3">
        <QuickLink
          icon={Shield}
          title="Access control"
          hint="Staff invites & RBAC"
          target="users"
        />
        <QuickLink
          icon={Database}
          title="Runtime config"
          hint="Booking & merchant defaults"
          target="booking"
        />
        <QuickLink
          icon={Globe}
          title="Integrations"
          hint="Fleetbase & Stripe status"
          target="fleetbase"
        />
      </div>

      <a
        href="/system?tab=ai"
        className="inline-flex text-sm font-medium text-secondary hover:underline"
      >
        Open AI usage (NIM metering) →
      </a>
    </div>
  );
}

function QuickLink({
  icon: Icon,
  title,
  hint,
  target,
}: {
  icon: typeof Server;
  title: string;
  hint: string;
  target: string;
}) {
  return (
    <button
      type="button"
      onClick={() => {
        window.dispatchEvent(new CustomEvent("settings-navigate", { detail: target }));
      }}
      className="rounded-xl border border-primary/10 bg-white p-4 text-left transition-colors hover:border-secondary/30 hover:bg-secondary/5"
    >
      <Icon className="h-5 w-5 text-secondary" />
      <p className="mt-2 text-sm font-semibold text-primary">{title}</p>
      <p className="text-xs text-muted">{hint}</p>
    </button>
  );
}
