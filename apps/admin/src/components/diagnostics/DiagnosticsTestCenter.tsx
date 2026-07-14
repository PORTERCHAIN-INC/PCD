"use client";

import { useMemo, useState } from "react";
import {
  Activity,
  AlertTriangle,
  FileText,
  FlaskConical,
  GitBranch,
  Layers,
  Radio,
  RefreshCw,
  Server,
  Truck,
  Zap,
} from "lucide-react";
import Link from "next/link";
import {
  ArchitectureChainView,
  HealthSummaryBar,
  ObservabilityPanel,
  TestCatalogCard,
  TestResultRow,
  ValidationProgressBar,
} from "@/components/diagnostics/DiagnosticsPrimitives";
import { Badge, Button, EmptyState, SectionCard, Spinner } from "@/components/crm/primitives";
import { SettingsPageHeader } from "@/components/settings/ui/SettingsPrimitives";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { useApiData } from "@/hooks/useApiData";
import {
  CHAOS_SCENARIOS,
  E2E_REPORT_FILES,
  TEST_CATEGORY_LABELS,
  diagnosticsApi,
  downloadReport,
  statusIcon,
  type E2EResult,
  type PlatformValidation,
  type TestCatalogItem,
  type TestResult,
} from "@/lib/diagnostics";

type Tab =
  | "tests"
  | "e2e"
  | "architecture"
  | "modules"
  | "workflows"
  | "events"
  | "fleetbase"
  | "chaos"
  | "observability"
  | "reports";

const TABS: { id: Tab; label: string; icon: React.ComponentType<{ className?: string }> }[] = [
  { id: "tests", label: "Integration tests", icon: FlaskConical },
  { id: "e2e", label: "E2E validation", icon: Activity },
  { id: "architecture", label: "Architecture", icon: GitBranch },
  { id: "modules", label: "Modules", icon: Layers },
  { id: "workflows", label: "Workflows", icon: Activity },
  { id: "events", label: "Event bus", icon: Radio },
  { id: "fleetbase", label: "Fleetbase sync", icon: Truck },
  { id: "chaos", label: "Chaos", icon: AlertTriangle },
  { id: "observability", label: "Observability", icon: Server },
  { id: "reports", label: "Reports", icon: FileText },
];

export function DiagnosticsTestCenter({
  embedded = false,
  onOpenHealth,
}: {
  embedded?: boolean;
  onOpenHealth?: () => void;
} = {}) {
  const { getApiToken } = useAdminAuth();
  const [tab, setTab] = useState<Tab>("tests");
  const [busy, setBusy] = useState<string | null>(null);
  const [results, setResults] = useState<Record<string, TestResult>>({});
  const [platformRun, setPlatformRun] = useState<PlatformValidation | null>(null);
  const [testCategory, setTestCategory] = useState<string | null>(null);
  const [eventFilter, setEventFilter] = useState("");
  const [chaosResult, setChaosResult] = useState<Record<string, unknown> | null>(null);
  const [reports, setReports] = useState<Record<string, string> | null>(null);
  const [workflowSim, setWorkflowSim] = useState<Record<string, unknown> | null>(null);
  const [e2eResult, setE2eResult] = useState<E2EResult | null>(null);

  const { data: catalog } = useApiData((t) => diagnosticsApi.listTests(t), [], {
    key: "tests-catalog",
    staleTime: 300_000,
  });
  const { data: health } = useApiData((t) => diagnosticsApi.health(t), [], {
    key: "health-dashboard",
    staleTime: 120_000,
  });
  const { data: architecture, loading: archLoading } = useApiData(
    (t) => (tab === "architecture" ? diagnosticsApi.architecture(t) : Promise.resolve(null)),
    [tab]
  );
  const { data: modules } = useApiData(
    (t) => (tab === "modules" ? diagnosticsApi.modules(t) : Promise.resolve(null)),
    [tab]
  );
  const { data: workflows } = useApiData(
    (t) => (tab === "workflows" ? diagnosticsApi.workflows(t) : Promise.resolve(null)),
    [tab]
  );
  const { data: events, loading: eventsLoading } = useApiData(
    (t) =>
      tab === "events" ? diagnosticsApi.events(t, eventFilter || undefined) : Promise.resolve(null),
    [tab, eventFilter]
  );
  const { data: fleetbase } = useApiData(
    (t) => (tab === "fleetbase" ? diagnosticsApi.fleetbaseSync(t) : Promise.resolve(null)),
    [tab]
  );
  const { data: observability } = useApiData(
    (t) => (tab === "observability" ? diagnosticsApi.observability(t) : Promise.resolve(null)),
    [tab]
  );

  const tests = catalog?.tests ?? [];
  const filteredTests = useMemo(
    () => (testCategory ? tests.filter((t) => t.category === testCategory) : tests),
    [tests, testCategory]
  );
  const testCategories = useMemo(() => [...new Set(tests.map((t) => t.category))], [tests]);

  async function runTest(id: string) {
    setBusy(id);
    try {
      const token = await getApiToken();
      const result = await diagnosticsApi.runTest(token, id);
      setResults((prev) => ({ ...prev, [id]: result }));
    } finally {
      setBusy(null);
    }
  }

  async function runAllTests() {
    setBusy("all");
    try {
      const token = await getApiToken();
      const result = await diagnosticsApi.runAllTests(token);
      setPlatformRun(result);
      const map: Record<string, TestResult> = {};
      result.results.forEach((r) => {
        map[r.id] = r;
      });
      setResults(map);
    } finally {
      setBusy(null);
    }
  }

  async function simulateWorkflow(id: string) {
    setBusy(id);
    try {
      const token = await getApiToken();
      const result = await diagnosticsApi.simulateWorkflow(token, id);
      setWorkflowSim(result);
    } finally {
      setBusy(null);
    }
  }

  async function runChaos(scenario: string) {
    setBusy(scenario);
    try {
      const token = await getApiToken();
      setChaosResult(await diagnosticsApi.chaos(token, scenario));
    } finally {
      setBusy(null);
    }
  }

  async function generateReports(writeFiles: boolean) {
    setBusy("reports");
    try {
      const token = await getApiToken();
      const result = await diagnosticsApi.generateReports(token, writeFiles);
      setReports(result.reports);
    } finally {
      setBusy(null);
    }
  }

  async function runE2E(writeFiles: boolean) {
    setBusy("e2e");
    try {
      const token = await getApiToken();
      const result = await diagnosticsApi.runE2E(token, {
        writeFiles,
        cleanup: true,
        merchantOrderCount: 100,
      });
      setE2eResult(result);
      setReports(result.reports);
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="space-y-5">
      {!embedded ? (
        <SettingsPageHeader
          title="System Tests & Diagnostics"
          description="29 automated checks across integrations, engines, infrastructure, and masterrule ADRs — run individually or as full platform validation."
          actions={
            <Link href="/system">
              <Button variant="outline">System health →</Button>
            </Link>
          }
        />
      ) : (
        <div className="flex justify-end">
          {onOpenHealth ? (
            <Button variant="outline" onClick={onOpenHealth}>
              View health →
            </Button>
          ) : (
            <Link href="/system">
              <Button variant="outline">View health →</Button>
            </Link>
          )}
        </div>
      )}

      {health && (
        <HealthSummaryBar
          overall={health.overall}
          summary={health.summary}
          checkedAt={health.checked_at}
          version={health.version}
          environment={health.environment}
        />
      )}

      <div className="flex flex-wrap gap-2">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            type="button"
            onClick={() => setTab(id)}
            className={`inline-flex items-center gap-1.5 rounded-xl px-3 py-2 text-sm font-medium transition ${
              tab === id
                ? "bg-secondary text-white shadow-sm"
                : "border border-primary/10 bg-white text-muted hover:bg-gray-50"
            }`}
          >
            <Icon className="h-4 w-4" />
            {label}
          </button>
        ))}
      </div>

      {tab === "tests" && (
        <div className="space-y-5">
          <SectionCard title="Platform validation" icon={<Zap className="h-4 w-4" />}>
            <div className="flex flex-wrap items-center gap-3">
              <Button onClick={runAllTests} disabled={busy === "all"}>
                {busy === "all" ? <RefreshCw className="h-4 w-4 animate-spin" /> : null}
                Run Complete Platform Validation
              </Button>
              {catalog && (
                <span className="text-sm text-muted">{catalog.count} tests in catalog</span>
              )}
            </div>
            {platformRun && (
              <div className="mt-4 space-y-2">
                <ValidationProgressBar
                  pass={platformRun.summary.pass}
                  warning={platformRun.summary.warning}
                  fail={platformRun.summary.fail}
                  total={platformRun.results.length}
                />
                <p className="text-xs text-muted">
                  {platformRun.execution_ms} ms total ·{" "}
                  {new Date(platformRun.ran_at).toLocaleString()}
                </p>
              </div>
            )}
          </SectionCard>

          <div className="flex flex-wrap gap-2">
            <CatBtn active={!testCategory} label="All" onClick={() => setTestCategory(null)} />
            {testCategories.map((c) => (
              <CatBtn
                key={c}
                active={testCategory === c}
                label={TEST_CATEGORY_LABELS[c] ?? c}
                onClick={() => setTestCategory(testCategory === c ? null : c)}
              />
            ))}
          </div>

          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {filteredTests.map((test) => (
              <TestCatalogCard
                key={test.id}
                test={test}
                busy={busy === test.id}
                result={results[test.id]}
                onRun={() => runTest(test.id)}
              />
            ))}
          </div>

          {Object.keys(results).length > 0 && (
            <SectionCard title="Recent results">
              <div className="space-y-2">
                {Object.values(results)
                  .sort((a, b) => b.ran_at.localeCompare(a.ran_at))
                  .slice(0, 10)
                  .map((r) => (
                    <TestResultRow key={`${r.id}-${r.ran_at}`} result={r} />
                  ))}
              </div>
            </SectionCard>
          )}
        </div>
      )}

      {tab === "e2e" && (
        <SectionCard title="Enterprise E2E validation" icon={<Activity className="h-4 w-4" />}>
          <p className="mb-3 text-sm text-muted">
            Automated validation across all 10 phases — system layer, forward/reverse logistics,
            merchant bulk, failure scenarios, event bus, notifications, consistency, and
            observability (masterrule §16).
          </p>
          <div className="flex flex-wrap gap-2">
            <Button onClick={() => runE2E(false)} disabled={busy === "e2e"}>
              {busy === "e2e" ? <RefreshCw className="h-4 w-4 animate-spin" /> : null}
              Run full E2E validation
            </Button>
            <Button variant="outline" onClick={() => runE2E(true)} disabled={busy === "e2e"}>
              Run + write reports to repo
            </Button>
          </div>
          {e2eResult && (
            <div className="mt-4 space-y-3">
              <div className="flex flex-wrap items-center gap-3">
                <Badge tone={e2eResult.production_ready ? "green" : "amber"}>
                  {statusIcon(e2eResult.overall)} {e2eResult.overall}
                </Badge>
                <span className="text-sm text-muted">
                  pass={e2eResult.summary.pass} warning={e2eResult.summary.warning} fail=
                  {e2eResult.summary.fails} blocker={e2eResult.summary.blockers}
                </span>
                <span className="text-xs text-muted">{e2eResult.execution_ms}ms</span>
              </div>
              <ul className="space-y-1 text-sm">
                {Object.entries(e2eResult.phases).map(([key, phase]) => (
                  <li key={key} className="flex justify-between rounded-lg border px-3 py-2">
                    <span>{String((phase as Record<string, unknown>).name ?? key)}</span>
                    <span>
                      {statusIcon(String((phase as Record<string, unknown>).overall ?? ""))}
                    </span>
                  </li>
                ))}
              </ul>
              <p className="text-xs text-muted">Reports: {E2E_REPORT_FILES.join(", ")}</p>
            </div>
          )}
        </SectionCard>
      )}

      {tab === "architecture" && (
        <SectionCard title="Architecture validation" icon={<GitBranch className="h-4 w-4" />}>
          {archLoading && <Spinner />}
          {architecture && (
            <div className="space-y-6">
              <p className="text-sm font-medium">
                Overall: {statusIcon(String(architecture.overall))} {String(architecture.overall)}
              </p>
              <ArchitectureChainView
                chain={(architecture.chain as Array<Record<string, unknown>>) ?? []}
              />
              {(architecture.adr_checklist as Array<Record<string, unknown>>)?.length > 0 && (
                <div>
                  <h4 className="mb-2 text-sm font-semibold">ADR checklist</h4>
                  <div className="grid gap-2 sm:grid-cols-2">
                    {(architecture.adr_checklist as Array<Record<string, unknown>>).map((adr) => (
                      <div key={String(adr.id)} className="rounded-lg border px-3 py-2 text-sm">
                        {statusIcon(String(adr.status))}{" "}
                        <span className="font-mono text-xs">{String(adr.id)}</span>{" "}
                        {String(adr.label)}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </SectionCard>
      )}

      {tab === "modules" && modules && (
        <SectionCard title="Module validation" icon={<Layers className="h-4 w-4" />}>
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {(
              modules.modules as Array<{
                id: string;
                name: string;
                status: string;
                logs?: string[];
              }>
            )?.map((m) => (
              <div key={m.id} className="rounded-xl border border-primary/10 px-3 py-2 text-sm">
                {statusIcon(m.status)} <span className="font-medium">{m.name}</span>
                {m.logs?.[0] && <p className="mt-1 text-xs text-muted">{m.logs[0]}</p>}
              </div>
            ))}
          </div>
        </SectionCard>
      )}

      {tab === "workflows" && workflows && (
        <SectionCard title="Business workflow simulator" icon={<Activity className="h-4 w-4" />}>
          <div className="space-y-4">
            {(workflows.scenarios as Array<Record<string, unknown>>)?.map((sc) => (
              <div key={String(sc.id)} className="rounded-xl border border-primary/10 p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p className="font-medium">{String(sc.name)}</p>
                  <Button
                    variant="outline"
                    disabled={busy === sc.id}
                    onClick={() => simulateWorkflow(String(sc.id))}
                  >
                    Simulate (dry run)
                  </Button>
                </div>
                <p className="mt-1 text-sm text-muted">
                  {statusIcon(String(sc.overall))} {String(sc.overall)}
                </p>
                <ol className="mt-2 grid gap-1 sm:grid-cols-2 text-sm">
                  {(sc.step_checks as Array<{ step: string; status: string; note?: string }>)?.map(
                    (step) => (
                      <li key={step.step} className="flex gap-1">
                        {statusIcon(step.status)} {step.step}
                      </li>
                    )
                  )}
                </ol>
              </div>
            ))}
          </div>
          {workflowSim && (
            <div className="mt-4 rounded-xl border bg-gray-50 p-4 text-sm">
              <p className="font-medium">Last simulation: {String(workflowSim.scenario_id)}</p>
              <pre className="mt-2 max-h-40 overflow-auto text-xs">
                {JSON.stringify(workflowSim, null, 2)}
              </pre>
            </div>
          )}
        </SectionCard>
      )}

      {tab === "events" && (
        <SectionCard title="Event bus inspector" icon={<Radio className="h-4 w-4" />}>
          <div className="mb-3 flex flex-wrap gap-2">
            {["order", "driver", "merchant", "customer"].map((f) => (
              <Button
                key={f}
                variant={eventFilter === f ? "primary" : "outline"}
                onClick={() => setEventFilter(f)}
              >
                {f}
              </Button>
            ))}
            <Button variant="outline" onClick={() => setEventFilter("")}>
              Clear
            </Button>
          </div>
          {eventsLoading && <Spinner />}
          {events && (
            <>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead>
                    <tr className="border-b text-muted">
                      <th className="py-2 pr-4">Event</th>
                      <th className="py-2 pr-4">Publisher</th>
                      <th className="py-2 pr-4">Consumers</th>
                      <th className="py-2 pr-4">Time</th>
                      <th className="py-2">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(events.events as Array<Record<string, unknown>>)?.map((e, i) => (
                      <tr key={i} className="border-b border-gray-100">
                        <td className="py-2 pr-4 font-mono text-xs">{String(e.event_name)}</td>
                        <td className="py-2 pr-4">{String(e.publisher)}</td>
                        <td className="py-2 pr-4 text-xs">
                          {String((e.consumers as string[])?.join(", ") ?? "—")}
                        </td>
                        <td className="py-2 pr-4 text-xs">{String(e.timestamp ?? "—")}</td>
                        <td className="py-2">{String(e.status)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {(events.dead_letter_queue as unknown[])?.length > 0 && (
                <div className="mt-4">
                  <h4 className="text-sm font-semibold text-red-700">Dead letter queue</h4>
                  <pre className="mt-2 max-h-40 overflow-auto rounded bg-red-50 p-2 text-xs">
                    {JSON.stringify(events.dead_letter_queue, null, 2)}
                  </pre>
                </div>
              )}
            </>
          )}
        </SectionCard>
      )}

      {tab === "fleetbase" && fleetbase && (
        <SectionCard title="Fleetbase sync monitor" icon={<Truck className="h-4 w-4" />}>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <Stat label="Pending" value={fleetbase.pending_sync} />
            <Stat label="Successful" value={fleetbase.successful_sync} />
            <Stat label="Failed" value={fleetbase.failed_sync} />
            <Stat label="Retry queue" value={fleetbase.retry_queue} />
          </div>
          {(fleetbase.dead_letters as unknown[])?.length > 0 && (
            <div className="mt-4 rounded-xl border border-red-200 bg-red-50/50 p-3 text-sm">
              <p className="font-medium text-red-800">
                {String((fleetbase.dead_letters as unknown[]).length)} dead letter job(s)
              </p>
            </div>
          )}
        </SectionCard>
      )}

      {tab === "chaos" && (
        <SectionCard title="Chaos & failure testing" icon={<AlertTriangle className="h-4 w-4" />}>
          <p className="mb-3 text-sm text-muted">
            Read-only resilience verification — validates retry, fallback, and recovery paths.
          </p>
          <div className="flex flex-wrap gap-2">
            {CHAOS_SCENARIOS.map((s) => (
              <Button key={s} variant="outline" disabled={busy === s} onClick={() => runChaos(s)}>
                {s.replace(/_/g, " ")}
              </Button>
            ))}
          </div>
          {chaosResult && (
            <pre className="mt-4 max-h-64 overflow-auto rounded-xl bg-gray-50 p-3 text-xs">
              {JSON.stringify(chaosResult, null, 2)}
            </pre>
          )}
        </SectionCard>
      )}

      {tab === "observability" && observability && (
        <SectionCard title="Observability" icon={<Server className="h-4 w-4" />}>
          <ObservabilityPanel data={observability} />
        </SectionCard>
      )}

      {tab === "reports" && (
        <SectionCard title="Production readiness reports" icon={<FileText className="h-4 w-4" />}>
          <div className="flex flex-wrap gap-2">
            <Button onClick={() => generateReports(false)} disabled={busy === "reports"}>
              Generate all reports
            </Button>
            <Button
              variant="outline"
              onClick={() => generateReports(true)}
              disabled={busy === "reports"}
            >
              Write to repo (local)
            </Button>
          </div>
          {reports ? (
            <ul className="mt-4 space-y-2">
              {Object.entries(reports).map(([name, content]) => (
                <li
                  key={name}
                  className="flex items-center justify-between rounded-xl border px-3 py-2 text-sm"
                >
                  <span>{name}</span>
                  <Button variant="outline" onClick={() => downloadReport(name, content)}>
                    Download
                  </Button>
                </li>
              ))}
            </ul>
          ) : (
            <EmptyState
              title="No reports yet"
              hint="Generate production readiness markdown reports."
            />
          )}
        </SectionCard>
      )}
    </div>
  );
}

function CatBtn({
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

function Stat({ label, value }: { label: string; value: unknown }) {
  return (
    <div className="rounded-xl border border-primary/10 bg-gray-50/80 p-3">
      <p className="text-xs text-muted">{label}</p>
      <p className="text-xl font-bold text-primary">{String(value ?? 0)}</p>
    </div>
  );
}
