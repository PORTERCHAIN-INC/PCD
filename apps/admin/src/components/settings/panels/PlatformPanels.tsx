"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { ArrowRight, Download, FileJson, Upload } from "lucide-react";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { relativeTime } from "@/lib/crmFormat";
import { Button } from "@/components/crm/primitives";
import { settingsApi, type AuditEntry, type SettingsDashboard } from "@/lib/settings";
import { SECTION_DESCRIPTIONS } from "@/lib/settings-metadata";
import { SettingsCard, SettingsPageHeader, StatTile } from "../ui/SettingsPrimitives";

function formatAuditDiff(oldValue: unknown, newValue: unknown): string {
  try {
    const text = JSON.stringify({ old: oldValue, new: newValue }, null, 2);
    // Huge vehicle/pricing blobs must not blow out the settings shell width
    if (text.length > 4000) {
      return `${text.slice(0, 4000)}\n… truncated (${text.length} chars)`;
    }
    return text;
  } catch {
    return "[unserializable diff]";
  }
}

export function AuditPanel() {
  const { getApiToken, isLoaded, isSignedIn } = useAdminAuth();
  const { data: logs = [], isLoading } = useQuery({
    queryKey: ["settings-audit"],
    enabled: isLoaded && (isSignedIn || process.env.NODE_ENV === "development"),
    queryFn: async () => settingsApi.audit(await getApiToken()),
  });

  return (
    <div className="min-w-0 max-w-full space-y-6">
      <SettingsPageHeader title="Audit log" description={SECTION_DESCRIPTIONS.audit} />
      <SettingsCard
        title="Configuration changes"
        description="Immutable record with actor, reason, and diff"
        className="min-w-0 overflow-hidden"
      >
        {isLoading ? (
          <p className="text-sm text-muted">Loading…</p>
        ) : (
          <div className="min-w-0 space-y-3">
            {logs.map((log, i) => (
              <AuditRow key={`${log.action}-${log.created_at}-${i}`} log={log} />
            ))}
            {!logs.length && (
              <p className="py-6 text-center text-sm text-muted">No settings audit entries yet</p>
            )}
          </div>
        )}
      </SettingsCard>
    </div>
  );
}

function AuditRow({ log }: { log: AuditEntry }) {
  return (
    <div className="min-w-0 overflow-hidden rounded-xl border border-primary/10 bg-gray-bg/30 p-4">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <p className="min-w-0 break-all font-mono text-sm font-semibold text-primary">
          {log.action}
        </p>
        <span className="shrink-0 text-xs text-muted">
          {log.created_at ? relativeTime(log.created_at) : "—"}
        </span>
      </div>
      <p className="mt-1 break-all text-xs text-muted">
        Actor: {log.actor_user_id || "system"} · {log.resource_type}
        {log.resource_id ? ` / ${log.resource_id}` : ""}
      </p>
      {log.reason && (
        <p className="mt-2 break-words text-sm text-primary/80">Reason: {log.reason}</p>
      )}
      {(log.old_value != null || log.new_value != null) && (
        <details className="mt-2 min-w-0">
          <summary className="cursor-pointer text-xs font-medium text-secondary">View diff</summary>
          <pre className="mt-2 max-h-40 max-w-full overflow-auto whitespace-pre-wrap break-all rounded-lg bg-white p-2 text-[10px] leading-relaxed">
            {formatAuditDiff(log.old_value, log.new_value)}
          </pre>
        </details>
      )}
    </div>
  );
}

export function PlatformPanel({
  variant,
  dash,
  onExport,
  onImport,
}: {
  variant: "backup" | "logs" | "developer" | "maintenance";
  dash?: SettingsDashboard;
  onExport: () => void;
  onImport: () => void;
}) {
  const titles = {
    backup: "Backup & restore",
    logs: "Logs & observability",
    developer: "Developer",
    maintenance: "System maintenance",
  };

  return (
    <div className="space-y-6">
      <SettingsPageHeader
        title={titles[variant]}
        description={SECTION_DESCRIPTIONS[variant]}
        actions={
          variant === "backup" ? (
            <>
              <Button variant="outline" onClick={onExport}>
                <Download className="h-4 w-4" /> Export config
              </Button>
              <Button variant="outline" onClick={onImport}>
                <Upload className="h-4 w-4" /> Import config
              </Button>
            </>
          ) : undefined
        }
      />

      {variant === "maintenance" && dash && (
        <div className="grid gap-3 sm:grid-cols-3">
          <StatTile label="Environment" value={dash.environment} />
          <StatTile label="Version" value={dash.version} />
          <StatTile
            label="Status"
            value={dash.system_status}
            tone={dash.system_status === "healthy" ? "success" : "warning"}
          />
        </div>
      )}

      {variant === "backup" && (
        <SettingsCard
          title="Configuration export"
          description="Exports SystemConfig rows — not database dumps"
        >
          <ul className="space-y-2 text-sm text-primary/80">
            <li className="flex gap-2">
              <FileJson className="h-4 w-4 shrink-0 text-secondary" />
              JSON export includes all runtime settings and defaults reference
            </li>
            <li className="flex gap-2">
              <FileJson className="h-4 w-4 shrink-0 text-secondary" />
              Import restores editable keys with full audit trail
            </li>
            <li className="flex gap-2">
              <FileJson className="h-4 w-4 shrink-0 text-secondary" />
              Database backups are managed at infrastructure level
            </li>
          </ul>
        </SettingsCard>
      )}

      {variant === "logs" && (
        <SettingsCard title="Log retention" description="masterrule §16 — observability">
          <p className="text-sm text-primary/80">
            Application logs, metrics, and traces are emitted by the API deployment. Configuration
            change history is available in the Audit section. Integration health is on the
            Dashboard.
          </p>
        </SettingsCard>
      )}

      {variant === "developer" && (
        <SettingsCard title="API & webhooks" description="Developer portal configuration">
          <p className="mb-4 text-sm text-primary/80">
            OpenAPI documentation, webhook endpoints, and SDK references are environment-managed.
            Merchant API keys are provisioned per merchant in the Merchant portal.
          </p>
          <p className="text-xs text-muted font-mono">
            GET /v1/admin/settings/export · POST /v1/admin/settings/import
          </p>
        </SettingsCard>
      )}
    </div>
  );
}

export function ModuleLinkPanel({
  sectionId,
}: {
  sectionId: string;
  moduleConfig?: Record<string, unknown>;
}) {
  return (
    <div className="space-y-6">
      <SettingsPageHeader
        title={sectionId.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
        description={SECTION_DESCRIPTIONS[sectionId]}
      />
      <p className="text-sm text-muted">
        This section moved into Commercial / Partners policy forms or the owning module nav.
      </p>
    </div>
  );
}

export function EnvManagedPanel({ sectionId }: { sectionId: string }) {
  const title = sectionId.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  return (
    <div className="space-y-6">
      <SettingsPageHeader
        title={title}
        description={SECTION_DESCRIPTIONS[sectionId] ?? "Environment-managed."}
      />
      <SettingsCard title="Credentials policy">
        <p className="text-sm text-primary/80">
          API keys and third-party credentials are stored in your secret manager /{" "}
          <code className="rounded bg-gray-bg px-1">env/.env</code> — never in Porterchain tables or
          this UI. Integration status appears on the Dashboard and integration panels.
        </p>
      </SettingsCard>
    </div>
  );
}
