"use client";

import { cn } from "@porterchain/ui/utils";
import { Shield } from "lucide-react";
import type { HealthComponent, MasterruleCheck, TestCatalogItem, TestResult } from "@/lib/diagnostics";
import { statusIcon, statusTone } from "@/lib/diagnostics";
import { SettingsCard } from "@/components/settings/ui/SettingsPrimitives";

const TONE_CLASS: Record<string, string> = {
  green: "border-green-200 bg-green-50/80 text-green-800",
  amber: "border-amber-200 bg-amber-50/80 text-amber-900",
  red: "border-red-200 bg-red-50/80 text-red-800",
  gray: "border-gray-200 bg-gray-50 text-gray-700",
};

export function HealthComponentCard({ component }: { component: HealthComponent }) {
  const tone = statusTone(component.status);
  return (
    <div className={cn("rounded-xl border p-4 shadow-sm transition hover:shadow-md", TONE_CLASS[tone])}>
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="font-semibold">{component.name}</p>
          <p className="truncate text-xs uppercase tracking-wide opacity-60">{component.id}</p>
        </div>
        <span className="text-xl" title={component.status}>
          {statusIcon(component.status)}
        </span>
      </div>
      <dl className="mt-3 space-y-1.5 text-sm">
        <Row label="Status" value={component.status} />
        {component.latency_ms != null && <Row label="Latency" value={`${component.latency_ms} ms`} />}
        {component.version && <Row label="Version" value={component.version} />}
        {component.last_sync && <Row label="Last sync" value={component.last_sync} />}
        {component.recovery_status !== "none" && <Row label="Recovery" value={component.recovery_status} />}
      </dl>
      {component.errors.length > 0 && (
        <ul className="mt-2 list-disc pl-4 text-xs text-red-700">
          {component.errors.map((e) => (
            <li key={e}>{e}</li>
          ))}
        </ul>
      )}
      {component.warnings.length > 0 && (
        <ul className="mt-2 list-disc pl-4 text-xs text-amber-900">
          {component.warnings.map((w) => (
            <li key={w}>{w}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-2">
      <dt className="text-muted">{label}</dt>
      <dd className="font-medium capitalize">{value}</dd>
    </div>
  );
}

export function HealthSummaryBar({
  overall,
  summary,
  checkedAt,
  version,
  environment,
}: {
  overall: string;
  summary: { healthy: number; warning: number; critical: number };
  checkedAt: string;
  version: string;
  environment: string;
}) {
  const tone = statusTone(overall);
  return (
    <div className={cn("rounded-2xl border p-5", TONE_CLASS[tone])}>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-sm font-medium opacity-80">Platform status</p>
          <p className="text-3xl font-bold capitalize tracking-tight">
            {statusIcon(overall)} {overall}
          </p>
        </div>
        <div className="flex flex-wrap gap-4 text-sm font-medium">
          <span>✅ {summary.healthy} healthy</span>
          <span>⚠ {summary.warning} warning</span>
          <span>❌ {summary.critical} critical</span>
        </div>
      </div>
      <p className="mt-3 text-xs opacity-70">
        v{version} · {environment} · checked {new Date(checkedAt).toLocaleString()}
      </p>
    </div>
  );
}

export function ProgressRing({
  healthy,
  warning,
  critical,
  total,
}: {
  healthy: number;
  warning: number;
  critical: number;
  total: number;
}) {
  const pct = total ? Math.round((healthy / total) * 100) : 0;
  return (
    <div className="flex flex-col items-center justify-center rounded-2xl border border-primary/10 bg-white px-8 py-5 shadow-sm">
      <div
        className="relative flex h-20 w-20 items-center justify-center rounded-full"
        style={{
          background: `conic-gradient(#16a34a ${pct}%, #e5e7eb ${pct}%)`,
        }}
      >
        <div className="flex h-14 w-14 flex-col items-center justify-center rounded-full bg-white text-center">
          <span className="text-lg font-bold text-primary">{pct}%</span>
        </div>
      </div>
      <p className="mt-2 text-xs text-muted">Health score</p>
      {critical > 0 && <p className="text-xs text-red-600">{critical} critical</p>}
      {warning > 0 && critical === 0 && <p className="text-xs text-amber-700">{warning} warning</p>}
    </div>
  );
}

export function MasterruleCompliancePanel({
  compliance,
}: {
  compliance: { overall: string; checks: MasterruleCheck[] };
}) {
  return (
    <SettingsCard
      title="Masterrule compliance"
      description="Architecture decision records and locked topology rules (masterrule §18–20)"
    >
      <div className="mb-3 flex items-center gap-2">
        <Shield className="h-4 w-4 text-secondary" />
        <span className="text-sm font-semibold capitalize">
          {statusIcon(compliance.overall)} {compliance.overall}
        </span>
      </div>
      <div className="grid gap-2 sm:grid-cols-2">
        {compliance.checks.map((c) => (
          <div key={c.id} className="flex items-start gap-2 rounded-lg border border-primary/5 px-3 py-2 text-sm">
            <span>{statusIcon(c.status)}</span>
            <div>
              <p className="font-medium">{c.label}</p>
              <p className="text-xs text-muted">{c.note}</p>
            </div>
          </div>
        ))}
      </div>
    </SettingsCard>
  );
}

export function TestCatalogCard({
  test,
  busy,
  result,
  onRun,
}: {
  test: TestCatalogItem;
  busy: boolean;
  result?: TestResult;
  onRun: () => void;
}) {
  const tone = result ? statusTone(result.status) : "gray";
  return (
    <div className={cn("flex flex-col rounded-xl border p-4", result ? TONE_CLASS[tone] : "border-primary/10 bg-white")}>
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="font-semibold text-primary">{test.name}</p>
          <p className="mt-0.5 text-xs text-muted">{test.description}</p>
          <p className="mt-1 text-[10px] uppercase tracking-wide text-muted">{test.masterrule}</p>
        </div>
        {result && <span>{statusIcon(result.status)}</span>}
      </div>
      <button
        type="button"
        disabled={busy}
        onClick={onRun}
        className="mt-3 rounded-lg border border-primary/15 bg-white px-3 py-1.5 text-xs font-medium hover:bg-gray-50 disabled:opacity-50"
      >
        {busy ? "Running…" : result ? "Re-run" : "Run test"}
      </button>
      {result && result.logs.length > 0 && (
        <pre className="mt-2 max-h-24 overflow-auto rounded bg-black/5 p-2 text-[10px]">{result.logs.join("\n")}</pre>
      )}
    </div>
  );
}

export function TestResultRow({
  result,
}: {
  result: {
    id: string;
    name: string;
    status: string;
    execution_ms: number;
    logs: string[];
    masterrule?: string;
  };
}) {
  const tone = statusTone(result.status);
  return (
    <div className={cn("rounded-xl border p-3", TONE_CLASS[tone])}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="font-medium">
          {statusIcon(result.status)} {result.name}
        </span>
        <span className="text-xs text-muted">{result.execution_ms} ms</span>
      </div>
      {result.masterrule && <p className="mt-0.5 text-[10px] uppercase text-muted">{result.masterrule}</p>}
      {result.logs.length > 0 && (
        <pre className="mt-2 max-h-32 overflow-auto rounded bg-black/5 p-2 text-xs">{result.logs.join("\n")}</pre>
      )}
    </div>
  );
}

export function ArchitectureChainView({ chain }: { chain: Array<Record<string, unknown>> }) {
  return (
    <div className="space-y-0">
      {chain.map((node, i) => (
        <div key={String(node.id)} className="relative flex gap-4 pb-4">
          {i < chain.length - 1 && (
            <div className="absolute left-[11px] top-6 h-full w-0.5 bg-primary/10" aria-hidden />
          )}
          <div
            className={cn(
              "relative z-10 mt-1 h-6 w-6 shrink-0 rounded-full border-2 bg-white text-center text-xs leading-[22px]",
              statusTone(String(node.status)) === "green" && "border-green-500",
              statusTone(String(node.status)) === "amber" && "border-amber-500",
              statusTone(String(node.status)) === "red" && "border-red-500"
            )}
          >
            {statusIcon(String(node.status))}
          </div>
          <div className="min-w-0 flex-1 rounded-xl border border-primary/10 bg-white px-4 py-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="font-medium text-primary">{String(node.node)}</p>
              {node.latency_ms != null && (
                <span className="text-xs text-muted">{String(node.latency_ms)} ms</span>
              )}
            </div>
            {node.downstream != null && (
              <p className="mt-1 text-xs text-muted">→ {String(node.downstream)}</p>
            )}
            {node.error != null && <p className="mt-1 text-xs text-red-600">{String(node.error)}</p>}
          </div>
        </div>
      ))}
    </div>
  );
}

export function ObservabilityPanel({ data }: { data: Record<string, unknown> }) {
  const queues = (data.queue_metrics as Record<string, number>) ?? {};
  const timeline = (data.system_timeline as Array<Record<string, unknown>>) ?? [];
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <div className="rounded-xl border border-primary/10 p-4">
        <h4 className="text-sm font-semibold">Queue depths</h4>
        <dl className="mt-2 space-y-1 text-sm">
          {Object.entries(queues).map(([k, v]) => (
            <div key={k} className="flex justify-between">
              <dt className="font-mono text-xs text-muted">{k}</dt>
              <dd className="font-medium">{v}</dd>
            </div>
          ))}
        </dl>
      </div>
      <div className="rounded-xl border border-primary/10 p-4">
        <h4 className="text-sm font-semibold">System timeline</h4>
        <ul className="mt-2 max-h-48 space-y-1 overflow-auto text-xs">
          {timeline.map((e, i) => (
            <li key={i} className="font-mono text-muted">
              {String(e.at ?? "—")} · {String(e.event_type)}
            </li>
          ))}
        </ul>
      </div>
      <div className="rounded-xl border border-primary/10 p-4 lg:col-span-2">
        <h4 className="text-sm font-semibold">Tracing</h4>
        <p className="mt-1 text-sm text-muted">
          Correlation header: <code className="rounded bg-gray-100 px-1">{String((data.correlation_ids as Record<string, unknown>)?.header ?? "X-Request-ID")}</code>
        </p>
        <p className="text-sm text-muted">
          Metrics: <code className="rounded bg-gray-100 px-1">{String((data.api_metrics as Record<string, unknown>)?.endpoint ?? "/metrics")}</code>
        </p>
      </div>
    </div>
  );
}

export function ValidationProgressBar({
  pass,
  warning,
  fail,
  total,
}: {
  pass: number;
  warning: number;
  fail: number;
  total: number;
}) {
  const passPct = total ? (pass / total) * 100 : 0;
  const warnPct = total ? (warning / total) * 100 : 0;
  const failPct = total ? (fail / total) * 100 : 0;
  return (
    <div className="space-y-2">
      <div className="flex h-3 overflow-hidden rounded-full bg-gray-100">
        <div className="bg-green-500 transition-all" style={{ width: `${passPct}%` }} />
        <div className="bg-amber-400 transition-all" style={{ width: `${warnPct}%` }} />
        <div className="bg-red-500 transition-all" style={{ width: `${failPct}%` }} />
      </div>
      <div className="flex gap-4 text-xs text-muted">
        <span>✅ Pass {pass}</span>
        <span>⚠ Warning {warning}</span>
        <span>❌ Fail {fail}</span>
      </div>
    </div>
  );
}
