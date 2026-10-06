"use client";

import { useDeferredValue, useEffect, useEffectEvent, useMemo, useState } from "react";
import { PageSkeleton } from "@porterchain/ui/loading";
import { AlertTriangle, RefreshCw, Search, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { cn } from "@porterchain/ui/utils";
import {
  HealthComponentCard,
  HealthSummaryBar,
  MasterruleCompliancePanel,
  ProgressRing,
} from "@/components/diagnostics/DiagnosticsPrimitives";
import { Badge, Button } from "@/components/crm/primitives";
import { SettingsCard, SettingsPageHeader } from "@/components/settings/ui/SettingsPrimitives";
import { useApiData } from "@/hooks/useApiData";
import {
  HEALTH_CATEGORY_LABELS,
  HEALTH_CATEGORY_ORDER,
  diagnosticsApi,
  filterComponents,
  type HealthDashboard,
} from "@/lib/diagnostics";

export function DiagnosticsHealthView({
  embedded = false,
  onOpenTests,
}: {
  embedded?: boolean;
  onOpenTests?: () => void;
} = {}) {
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [query, setQuery] = useState("");
  const deferredQuery = useDeferredValue(query);
  const [category, setCategory] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string | null>(null);

  const { data, loading, error, refetch, isFetching } = useApiData(
    (t) => diagnosticsApi.health(t),
    [],
    { key: "health-dashboard", staleTime: 120_000 }
  );

  const tickHealth = useEffectEvent(() => {
    void refetch();
  });

  useEffect(() => {
    if (!autoRefresh) return;
    const id = setInterval(() => tickHealth(), 60_000);
    return () => clearInterval(id);
  }, [autoRefresh]);

  const filtered = useMemo(
    () => (data ? filterComponents(data.components, deferredQuery, category, statusFilter) : []),
    [data, deferredQuery, category, statusFilter]
  );

  const issues = data?.components.filter((c) => c.status !== "healthy") ?? [];

  return (
    <div className="space-y-6">
      {!embedded ? (
        <SettingsPageHeader
          title="Health"
          description="Real-time validation of the locked Porterchain topology — portals, engines, integrations, and infrastructure per masterrule §1, §16, and Appendix B."
          actions={
            <>
              <label className="flex items-center gap-2 text-sm text-muted">
                <input
                  type="checkbox"
                  checked={autoRefresh}
                  onChange={(e) => setAutoRefresh(e.target.checked)}
                />
                Auto-refresh 60s
              </label>
              <Button variant="outline" disabled={isFetching} onClick={() => void refetch()}>
                <RefreshCw className={cn("h-4 w-4", isFetching && "animate-spin")} />
                Refresh
              </Button>
              <Link href="/system?tab=tests">
                <Button>Run tests →</Button>
              </Link>
            </>
          }
        />
      ) : (
        <div className="flex flex-wrap items-center justify-end gap-3">
          <label className="flex items-center gap-2 text-sm text-muted">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
            />
            Auto-refresh 60s
          </label>
          <Button variant="outline" disabled={isFetching} onClick={() => void refetch()}>
            <RefreshCw className={cn("h-4 w-4", isFetching && "animate-spin")} />
            Refresh
          </Button>
          {onOpenTests ? (
            <Button onClick={onOpenTests}>Run tests →</Button>
          ) : (
            <Link href="/system?tab=tests">
              <Button>Run tests →</Button>
            </Link>
          )}
        </div>
      )}

      {loading && !data && (
        <div className="flex justify-center py-16">
          <PageSkeleton rows={3} />
        </div>
      )}
      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">
          {error}
        </div>
      )}

      {data && (
        <>
          {data.auth_sli && Object.keys(data.auth_sli).length > 0 ? (
            <SettingsCard title="Staff auth SLI (this API process)">
              <div className="flex flex-wrap gap-2 text-xs">
                {Object.entries(data.auth_sli).map(([kind, results]) => (
                  <span
                    key={kind}
                    className="rounded-lg border border-primary/10 bg-gray-bg/60 px-2.5 py-1.5 font-mono text-primary"
                  >
                    {kind}:{" "}
                    {Object.entries(results)
                      .map(([r, n]) => `${r}=${n}`)
                      .join(" · ")}
                  </span>
                ))}
              </div>
              <p className="mt-2 text-xs text-muted">
                Counters reset on API restart. Also scraped as{" "}
                <code className="font-mono">porterchain_auth_events_total</code>.
              </p>
            </SettingsCard>
          ) : null}
          {data.auth_posture ? (
            <SettingsCard title="Staff IdP cookie posture">
              <dl className="grid gap-2 text-sm sm:grid-cols-2">
                <div>
                  <dt className="text-xs text-muted">Domain mode</dt>
                  <dd className="font-mono text-primary">{data.auth_posture.cookie_domain_mode}</dd>
                </div>
                <div>
                  <dt className="text-xs text-muted">Cookie</dt>
                  <dd className="font-mono text-primary">
                    Secure={String(data.auth_posture.cookie_secure)} · SameSite=
                    {data.auth_posture.cookie_samesite}
                    {data.auth_posture.cookie_domain
                      ? ` · Domain=${data.auth_posture.cookie_domain}`
                      : " · host-only"}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs text-muted">Local bypass</dt>
                  <dd className="font-mono text-primary">
                    {data.auth_posture.auth_bypass_allowed ? "allowed" : "disabled"}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs text-muted">IdP</dt>
                  <dd className="font-mono text-primary">{data.auth_posture.staff_idp}</dd>
                </div>
              </dl>
            </SettingsCard>
          ) : null}
          <div className="grid gap-4 lg:grid-cols-[1fr_auto]">
            <HealthSummaryBar
              overall={data.overall}
              summary={data.summary}
              checkedAt={data.checked_at}
              version={data.version}
              environment={data.environment}
            />
            <ProgressRing
              healthy={data.summary.healthy}
              warning={data.summary.warning}
              critical={data.summary.critical}
              total={data.components.length}
            />
          </div>

          {issues.length > 0 && (
            <SettingsCard
              title="Attention required"
              description={`${issues.length} component(s) need review`}
            >
              <ul className="space-y-2 text-sm">
                {issues.slice(0, 8).map((c) => (
                  <li
                    key={c.id}
                    className="flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50/50 px-3 py-2"
                  >
                    <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-700" />
                    <div>
                      <span className="font-medium">{c.name}</span>
                      <span className="ml-2 text-xs uppercase text-amber-800">{c.status}</span>
                      {(c.errors[0] || c.warnings[0]) && (
                        <p className="mt-0.5 text-xs text-muted">{c.errors[0] || c.warnings[0]}</p>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            </SettingsCard>
          )}

          <MasterruleCompliancePanel compliance={data.masterrule_compliance} />

          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="relative max-w-md flex-1">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search components…"
                className="w-full rounded-xl border border-primary/10 py-2 pl-9 pr-3 text-sm"
              />
            </div>
            <div className="flex flex-wrap gap-2">
              <FilterChip
                active={!statusFilter}
                onClick={() => setStatusFilter(null)}
                label="All statuses"
              />
              <FilterChip
                active={statusFilter === "healthy"}
                onClick={() => setStatusFilter("healthy")}
                label="Healthy"
              />
              <FilterChip
                active={statusFilter === "warning"}
                onClick={() => setStatusFilter("warning")}
                label="Warning"
              />
              <FilterChip
                active={statusFilter === "critical"}
                onClick={() => setStatusFilter("critical")}
                label="Critical"
              />
            </div>
          </div>

          <div className="flex flex-wrap gap-2">
            <CategoryChip
              active={!category}
              label="All"
              count={data.components.length}
              onClick={() => setCategory(null)}
            />
            {HEALTH_CATEGORY_ORDER.map((cat) => {
              const g = data.groups?.[cat];
              if (!g) return null;
              return (
                <CategoryChip
                  key={cat}
                  active={category === cat}
                  label={HEALTH_CATEGORY_LABELS[cat] ?? cat}
                  count={g.items.length}
                  onClick={() => setCategory(category === cat ? null : cat)}
                  warning={g.summary.warning + g.summary.critical}
                />
              );
            })}
          </div>

          {category || query || statusFilter ? (
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
              {filtered.map((c) => (
                <HealthComponentCard key={c.id} component={c} />
              ))}
            </div>
          ) : (
            HEALTH_CATEGORY_ORDER.map((cat) => {
              const group = data.groups?.[cat];
              if (!group?.items.length) return null;
              return (
                <section key={cat} className="space-y-3">
                  <div className="flex items-center justify-between">
                    <h2 className="text-sm font-semibold text-primary">{group.label}</h2>
                    <div className="flex gap-2 text-xs text-muted">
                      <span>✅ {group.summary.healthy}</span>
                      {group.summary.warning > 0 && <span>⚠ {group.summary.warning}</span>}
                      {group.summary.critical > 0 && <span>❌ {group.summary.critical}</span>}
                    </div>
                  </div>
                  <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                    {group.items.map((c) => (
                      <HealthComponentCard key={c.id} component={c} />
                    ))}
                  </div>
                </section>
              );
            })
          )}
        </>
      )}
    </div>
  );
}

function FilterChip({
  active,
  label,
  onClick,
}: {
  active: boolean;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-full px-3 py-1 text-xs font-medium ${
        active ? "bg-secondary text-white" : "bg-gray-100 text-muted hover:bg-gray-200"
      }`}
    >
      {label}
    </button>
  );
}

function CategoryChip({
  active,
  label,
  count,
  warning,
  onClick,
}: {
  active: boolean;
  label: string;
  count: number;
  warning?: number;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`inline-flex items-center gap-1.5 rounded-xl border px-3 py-1.5 text-xs font-medium transition ${
        active
          ? "border-secondary bg-secondary/10 text-secondary"
          : "border-primary/10 bg-white hover:bg-gray-50"
      }`}
    >
      {label}
      <span className="rounded-full bg-black/5 px-1.5 py-0.5">{count}</span>
      {warning ? <span className="text-amber-700">⚠{warning}</span> : null}
    </button>
  );
}

export function DiagnosticsHealthCompact({ data }: { data: HealthDashboard | null }) {
  if (!data) return null;
  return (
    <div className="flex items-center gap-2 text-sm">
      <ShieldCheck className="h-4 w-4 text-muted" />
      <Badge
        tone={data.overall === "healthy" ? "green" : data.overall === "warning" ? "amber" : "red"}
      >
        {data.overall}
      </Badge>
      <span className="text-muted">
        {data.summary.healthy}/{data.components.length} healthy
      </span>
    </div>
  );
}
