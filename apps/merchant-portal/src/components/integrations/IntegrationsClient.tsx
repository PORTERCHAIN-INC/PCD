"use client";

import ConnectionsStatus from "@/components/integrations/ConnectionsStatus";
import ShopifyConnectCard from "@/components/integrations/ShopifyConnectCard";
import Button from "@/components/ui/Button";
import { useMerchantAuth } from "@/hooks/useMerchantAuth";
import {
  integrationsApi,
  WEBHOOK_EVENT_PRESETS,
  type ApiDoc,
  type ApiKeyRecord,
  type EventCatalogItem,
  type IntegrationsOverview,
  type RateLimitRow,
  type WebhookDelivery,
  type WebhookRecord,
} from "@/lib/integrations";
import { formatDate } from "@/lib/utils";
import { PageSkeleton } from "@porterchain/ui/loading";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useSearchParams } from "next/navigation";
import { useState } from "react";

type Tab = "overview" | "keys" | "webhooks" | "logs" | "usage" | "sandbox" | "docs";

const TABS: { id: Tab; label: string }[] = [
  { id: "overview", label: "Overview" },
  { id: "keys", label: "API keys" },
  { id: "webhooks", label: "Webhooks" },
  { id: "logs", label: "Webhook logs" },
  { id: "usage", label: "API usage" },
  { id: "sandbox", label: "Sandbox" },
  { id: "docs", label: "Documentation" },
];

function parseIntegrationsTab(value: string | null): Tab {
  if (value && TABS.some((t) => t.id === value)) return value as Tab;
  return "overview";
}

export default function IntegrationsClient() {
  const { getApiToken, orgId, isLoaded, isSignedIn } = useMerchantAuth();
  const qc = useQueryClient();
  const searchParams = useSearchParams();
  const [tab, setTab] = useState<Tab>(() => parseIntegrationsTab(searchParams.get("tab")));
  const keyOrg = orgId ?? null;
  const ready = Boolean(isLoaded && isSignedIn && orgId);

  const query = useQuery({
    queryKey: ["merchant-integrations", keyOrg],
    enabled: ready,
    queryFn: async () => {
      const token = await getApiToken();
      const [ov, keyRows, hookRows, logRows, doc, ev, rateData] = await Promise.all([
        integrationsApi.overview(token, orgId),
        integrationsApi.listKeys(token, orgId),
        integrationsApi.listWebhooks(token, orgId),
        integrationsApi.webhookLogs(token, orgId),
        integrationsApi.documentation(token, orgId),
        integrationsApi.events(token, orgId),
        integrationsApi.rateLimits(token, orgId),
      ]);
      return {
        overview: ov,
        keys: keyRows,
        webhooks: hookRows,
        logs: logRows,
        docs: doc,
        events: ev.events,
        limits: rateData.limits,
      };
    },
  });

  const overview = query.data?.overview ?? null;
  const keys = query.data?.keys ?? [];
  const webhooks = query.data?.webhooks ?? [];
  const logs = query.data?.logs ?? [];
  const docs = query.data?.docs ?? null;
  const events = query.data?.events ?? [];
  const limits = query.data?.limits ?? [];
  const loading = query.isLoading && !query.data;
  const error = query.error instanceof Error ? query.error.message : null;

  const load = () => qc.invalidateQueries({ queryKey: ["merchant-integrations", keyOrg] });

  if (!isLoaded || !orgId) {
    return <PageSkeleton rows={4} />;
  }
  if (!isSignedIn) {
    return <p className="text-muted">Please sign in.</p>;
  }

  return (
    <div className="space-y-6">
      <h1 className="sr-only">Integrations</h1>
      <ConnectionsStatus />

      <details className="group rounded-3xl border border-primary/10 bg-white">
        <summary className="flex min-h-14 cursor-pointer list-none items-center justify-between px-5 text-base font-bold text-primary sm:px-6">
          Shopify setup
          <span aria-hidden className="text-slate-500 transition group-open:rotate-180">
            ⌄
          </span>
        </summary>
        <div className="space-y-3 border-t border-primary/10 p-4 sm:p-6">
          <ShopifyConnectCard />
          <p className="text-sm text-slate-600">
            Partners call <code className="rounded bg-gray-bg px-1">/v1/merchant-api</code> with{" "}
            <code className="rounded bg-gray-bg px-1">X-Api-Key</code>.{" "}
            <a href="/shopify" className="font-semibold text-secondary underline">
              Open Shopify page
            </a>
          </p>
        </div>
      </details>

      {error && !overview ? (
        <div className="space-y-4">
          <p className="text-red-600">{error}</p>
          <Button onClick={() => void load()}>Retry</Button>
        </div>
      ) : null}

      {loading && !overview ? <PageSkeleton rows={4} /> : null}

      {overview ? (
        <>
          {error ? <p className="text-sm text-red-600">{error}</p> : null}

          <nav
            className="ops-tab-rail rounded-2xl border border-primary/10 bg-white"
            aria-label="Integrations"
          >
            {TABS.map((t) => (
              <button
                key={t.id}
                type="button"
                onClick={() => setTab(t.id)}
                className={`min-h-10 shrink-0 rounded-xl px-3 py-1.5 text-sm font-medium whitespace-nowrap transition ${
                  tab === t.id ? "bg-primary text-white" : "text-muted hover:bg-primary/5"
                }`}
              >
                {t.label}
              </button>
            ))}
          </nav>

          {tab === "overview" && <OverviewTab overview={overview} limits={limits} />}
          {tab === "keys" && (
            <KeysTab
              keys={keys}
              limits={limits}
              onRefresh={load}
              getToken={getApiToken}
              orgId={orgId}
            />
          )}
          {tab === "webhooks" && (
            <WebhooksTab
              webhooks={webhooks}
              events={events}
              onRefresh={load}
              getToken={getApiToken}
              orgId={orgId}
            />
          )}
          {tab === "logs" && (
            <LogsTab logs={logs} onRefresh={load} getToken={getApiToken} orgId={orgId} />
          )}
          {tab === "usage" && <UsageTab overview={overview} />}
          {tab === "sandbox" && (
            <SandboxTab
              enabled={overview.sandbox_mode}
              onRefresh={load}
              getToken={getApiToken}
              orgId={orgId}
            />
          )}
          {tab === "docs" && docs && <DocsTab docs={docs} />}
        </>
      ) : null}
    </div>
  );
}

function OverviewTab({
  overview,
  limits,
}: {
  overview: IntegrationsOverview;
  limits: RateLimitRow[];
}) {
  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Metric label="API keys" value={String(overview.api_keys_count)} />
        <Metric label="Webhooks" value={String(overview.webhooks_count)} />
        <Metric label="Requests (7d)" value={String(overview.usage.total_requests)} />
        <Metric label="Test preference" value={overview.sandbox_mode ? "On" : "Off"} />
      </div>
      <section className="rounded-2xl border border-primary/10 bg-white p-6">
        <h2 className="font-semibold text-primary">Rate limits</h2>
        <ul className="mt-4 space-y-2 text-sm">
          {limits.length === 0 && <li className="text-muted">No active keys</li>}
          {limits.map((l) => (
            <li key={l.api_key_id} className="flex justify-between gap-4">
              <span>
                {l.name} <span className="text-muted">({l.environment})</span>
              </span>
              <span className={l.throttled ? "text-red-600" : "text-muted"}>
                {l.requests_last_minute}/{l.rate_limit_per_minute} per min
              </span>
            </li>
          ))}
        </ul>
      </section>
      <section className="rounded-2xl border border-primary/10 bg-white p-6">
        <h2 className="font-semibold text-primary">Recent webhook deliveries</h2>
        <DeliveryTable rows={overview.recent_webhook_deliveries} compact />
      </section>
    </div>
  );
}

function KeysTab({
  keys,
  limits,
  onRefresh,
  getToken,
  orgId,
}: {
  keys: ApiKeyRecord[];
  limits: RateLimitRow[];
  onRefresh: () => Promise<void>;
  getToken: () => Promise<string>;
  orgId?: string;
}) {
  const [name, setName] = useState("");
  const [environment, setEnvironment] = useState<"sandbox" | "production">("sandbox");
  const [newSecret, setNewSecret] = useState<string | null>(null);

  const create = async (e: React.FormEvent) => {
    e.preventDefault();
    if (environment === "production") {
      if (
        !window.confirm(
          "Create a production API key? It can book live capacity and is Owner-gated on the server."
        )
      ) {
        return;
      }
    }
    const token = await getToken();
    const row = await integrationsApi.createKey(
      token,
      { name: name || "API Key", environment },
      orgId
    );
    setNewSecret(row.secret || null);
    setName("");
    await onRefresh();
  };

  const revoke = async (id: string) => {
    const token = await getToken();
    await integrationsApi.revokeKey(token, id, orgId);
    await onRefresh();
  };

  return (
    <div className="space-y-6">
      {newSecret && (
        <SecretBanner secret={newSecret} label="API key" onDismiss={() => setNewSecret(null)} />
      )}
      <form
        onSubmit={(e) => void create(e)}
        className="flex flex-wrap items-end gap-3 rounded-2xl border border-primary/10 bg-white p-6"
      >
        <div>
          <label className="text-sm font-medium">Key name</label>
          <input
            className="mt-1 block rounded-xl border border-primary/15 px-3 py-2 text-sm"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Production integration"
          />
        </div>
        <div>
          <label className="text-sm font-medium">Environment</label>
          <select
            className="mt-1 block rounded-xl border border-primary/15 px-3 py-2 text-sm"
            value={environment}
            onChange={(e) => setEnvironment(e.target.value as "sandbox" | "production")}
          >
            <option value="sandbox">Sandbox</option>
            <option value="production">Production</option>
          </select>
        </div>
        <Button type="submit">Generate API key</Button>
      </form>
      <section className="rounded-2xl border border-primary/10 bg-white p-6">
        <h2 className="font-semibold text-primary">Active keys</h2>
        <ul className="mt-4 divide-y divide-primary/5">
          {keys.map((k) => {
            const limit = limits.find((l) => l.api_key_id === k.id);
            return (
              <li
                key={k.id}
                className="flex flex-wrap items-center justify-between gap-3 py-3 text-sm"
              >
                <div>
                  <p className="font-medium">{k.name}</p>
                  <p className="font-mono text-xs text-muted">
                    {k.key_prefix}… · {k.environment} · {k.rate_limit_per_minute}/min
                    {limit?.throttled && " · throttled"}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    className="text-xs text-red-600"
                    onClick={() => void revoke(k.id)}
                  >
                    Revoke
                  </button>
                </div>
              </li>
            );
          })}
          {keys.length === 0 && <li className="py-4 text-muted">No API keys yet</li>}
        </ul>
      </section>
    </div>
  );
}

function WebhooksTab({
  webhooks,
  events,
  onRefresh,
  getToken,
  orgId,
}: {
  webhooks: WebhookRecord[];
  events: EventCatalogItem[];
  onRefresh: () => Promise<void>;
  getToken: () => Promise<string>;
  orgId?: string;
}) {
  const [url, setUrl] = useState("");
  const [selectedEvents, setSelectedEvents] = useState<string[]>([
    "order.booked",
    "order.delivered",
  ]);
  const [environment, setEnvironment] = useState<"sandbox" | "production">("sandbox");
  const [newSecret, setNewSecret] = useState<string | null>(null);

  const toggleEvent = (ev: string) => {
    setSelectedEvents((prev) => (prev.includes(ev) ? prev.filter((e) => e !== ev) : [...prev, ev]));
  };

  const create = async (e: React.FormEvent) => {
    e.preventDefault();
    if (environment === "production") {
      if (
        !window.confirm(
          "Register a production webhook? It will only receive live (non-sandbox) order events."
        )
      ) {
        return;
      }
    }
    const token = await getToken();
    const row = await integrationsApi.createWebhook(
      token,
      { url, events: selectedEvents, environment },
      orgId
    );
    if (row.signing_secret) setNewSecret(row.signing_secret);
    setUrl("");
    await onRefresh();
  };

  const test = async (id: string) => {
    const token = await getToken();
    await integrationsApi.testWebhook(token, id, orgId);
    await onRefresh();
  };

  const rotate = async (id: string) => {
    const token = await getToken();
    const row = await integrationsApi.rotateWebhookSecret(token, id, orgId);
    if (row.signing_secret) setNewSecret(row.signing_secret);
    await onRefresh();
  };

  const remove = async (id: string) => {
    const token = await getToken();
    await integrationsApi.deleteWebhook(token, id, orgId);
    await onRefresh();
  };

  return (
    <div className="space-y-6">
      {newSecret && (
        <SecretBanner
          secret={newSecret}
          label="Webhook signing secret"
          onDismiss={() => setNewSecret(null)}
        />
      )}
      <form
        onSubmit={(e) => void create(e)}
        className="space-y-4 rounded-2xl border border-primary/10 bg-white p-6"
      >
        <h2 className="font-semibold text-primary">Add webhook</h2>
        <input
          className="block w-full rounded-xl border border-primary/15 px-3 py-2 text-sm"
          placeholder="https://your-app.com/webhooks/porterchain"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
        />
        <select
          className="block w-full rounded-xl border border-primary/15 px-3 py-2 text-sm"
          value={environment}
          onChange={(e) => setEnvironment(e.target.value as "sandbox" | "production")}
        >
          <option value="sandbox">Sandbox</option>
          <option value="production">Production</option>
        </select>
        <div className="flex flex-wrap gap-2">
          {WEBHOOK_EVENT_PRESETS.map((ev) => (
            <button
              key={ev}
              type="button"
              onClick={() => toggleEvent(ev)}
              className={`rounded-full px-3 py-1 text-xs ${
                selectedEvents.includes(ev) ? "bg-primary text-white" : "bg-primary/5 text-muted"
              }`}
            >
              {ev}
            </button>
          ))}
        </div>
        <Button type="submit">Create webhook</Button>
      </form>
      <section className="rounded-2xl border border-primary/10 bg-white p-6">
        <h2 className="font-semibold text-primary">Webhooks</h2>
        <ul className="mt-4 space-y-4">
          {webhooks.map((h) => (
            <li key={h.id} className="rounded-xl border border-primary/10 p-4 text-sm">
              <p className="font-medium break-all">{h.url}</p>
              <p className="mt-1 text-xs text-muted">
                {h.environment || "production"} · {h.events.join(", ") || "all events"}
              </p>
              <div className="mt-3 flex flex-wrap gap-2">
                <Button size="sm" variant="outline" onClick={() => void test(h.id)}>
                  Send test
                </Button>
                <Button size="sm" variant="outline" onClick={() => void rotate(h.id)}>
                  Rotate secret
                </Button>
                <button
                  type="button"
                  className="text-xs text-red-600"
                  onClick={() => void remove(h.id)}
                >
                  Delete
                </button>
              </div>
            </li>
          ))}
          {webhooks.length === 0 && <li className="text-muted">No webhooks configured</li>}
        </ul>
      </section>
      <section className="rounded-2xl border border-primary/10 bg-white p-6">
        <h2 className="font-semibold text-primary">Event catalog</h2>
        <ul className="mt-4 max-h-64 space-y-2 overflow-y-auto text-sm">
          {events.map((ev) => (
            <li key={ev.event} className="flex justify-between gap-4">
              <code className="text-xs">{ev.event}</code>
              <span className="text-muted">{ev.description}</span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}

function LogsTab({
  logs,
  onRefresh,
  getToken,
  orgId,
}: {
  logs: WebhookDelivery[];
  onRefresh: () => Promise<void>;
  getToken: () => Promise<string>;
  orgId?: string;
}) {
  const retry = async (id: string) => {
    const token = await getToken();
    await integrationsApi.retryDelivery(token, id, orgId);
    await onRefresh();
  };

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted">
        Delivery history with automatic retry (up to 3 attempts). Failed deliveries can be retried
        manually.
      </p>
      <DeliveryTable rows={logs} onRetry={retry} />
    </div>
  );
}

function UsageTab({ overview }: { overview: IntegrationsOverview }) {
  const usage = overview.usage;
  const maxDay = Math.max(...usage.by_day.map((d) => d.count), 1);

  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-3">
        <Metric label="Total requests" value={String(usage.total_requests)} />
        <Metric label="Errors" value={String(usage.error_requests)} />
        <Metric label="Sandbox" value={String(usage.by_environment.sandbox ?? 0)} />
      </div>
      <section className="rounded-2xl border border-primary/10 bg-white p-6">
        <h2 className="font-semibold text-primary">Daily API usage</h2>
        <div className="mt-4 flex h-32 items-end gap-2">
          {usage.by_day.map((d) => (
            <div key={d.date} className="flex flex-1 flex-col items-center gap-1">
              <div
                className="w-full rounded-t bg-secondary/80"
                style={{ height: `${Math.max(8, (d.count / maxDay) * 100)}%` }}
              />
              <span className="text-[10px] text-muted">{d.date.slice(5)}</span>
            </div>
          ))}
        </div>
      </section>
      <section className="rounded-2xl border border-primary/10 bg-white p-6">
        <h2 className="font-semibold text-primary">Top endpoints</h2>
        <ul className="mt-4 space-y-2 text-sm">
          {usage.by_path.map((p) => (
            <li key={p.path} className="flex justify-between">
              <code className="text-xs">{p.path}</code>
              <span>{p.count}</span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}

function SandboxTab({
  enabled,
  onRefresh,
  getToken,
  orgId,
}: {
  enabled: boolean;
  onRefresh: () => Promise<void>;
  getToken: () => Promise<string>;
  orgId?: string;
}) {
  const [goLiveConfirm, setGoLiveConfirm] = useState("");
  const [purgeConfirm, setPurgeConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState<string | null>(null);
  const [consoleAction, setConsoleAction] = useState("list_orders");
  const [consoleOut, setConsoleOut] = useState<string | null>(null);
  const [simOrderId, setSimOrderId] = useState("");

  const setPreference = async (next: boolean) => {
    setBusy(true);
    setNote(null);
    try {
      if (enabled && !next && goLiveConfirm.trim().toUpperCase() !== "LIVE") {
        setNote("Type LIVE to switch the default preference off.");
        return;
      }
      const token = await getToken();
      await integrationsApi.setSandbox(token, next, orgId);
      setGoLiveConfirm("");
      await onRefresh();
      setNote(
        next ? "Test preference on — banner shows across the portal." : "Test preference off."
      );
    } catch (e) {
      setNote(e instanceof Error ? e.message : "Could not update preference");
    } finally {
      setBusy(false);
    }
  };

  const runConsole = async () => {
    setBusy(true);
    setNote(null);
    try {
      const token = await getToken();
      const payload =
        consoleAction === "create_booking"
          ? {
              environment: "sandbox",
              booking: {
                pickup: {
                  formatted: "100 King St W, Toronto",
                  postal: "M5X 1A1",
                  lat: 43.65,
                  lng: -79.38,
                },
                dropoff: {
                  formatted: "200 Bay St, Toronto",
                  postal: "M5J 2J2",
                  lat: 43.65,
                  lng: -79.38,
                },
                scheduled_at: new Date().toISOString(),
                vehicle_class: "cargo_van",
                is_sandbox: true,
              },
            }
          : consoleAction === "simulate_lifecycle"
            ? { order_id: simOrderId, deliver_webhooks: false, until_state: "DELIVERED" }
            : { limit: 5 };
      const result = await integrationsApi.console(token, consoleAction, payload, orgId);
      setConsoleOut(JSON.stringify(result, null, 2));
    } catch (e) {
      setConsoleOut(e instanceof Error ? e.message : "Console failed");
    } finally {
      setBusy(false);
    }
  };

  const purge = async () => {
    setBusy(true);
    setNote(null);
    try {
      const token = await getToken();
      const result = await integrationsApi.purgeSandbox(token, purgeConfirm, orgId);
      setPurgeConfirm("");
      setNote(`${result.message} (${result.cancelled} cancelled)`);
      await onRefresh();
    } catch (e) {
      setNote(e instanceof Error ? e.message : "Purge failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border border-primary/10 bg-white p-6">
        <h2 className="font-semibold text-primary">Booking preference</h2>
        <p className="mt-2 text-sm text-muted">
          Portal reminder only — it does not force every booking into dry-run. Partner API uses{" "}
          <code className="rounded bg-gray-bg px-1">pk_sandbox_</code> /{" "}
          <code className="rounded bg-gray-bg px-1">pk_production_</code>. Book delivery has its own
          Live|Test control.
        </p>
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <span className={`text-sm font-medium ${enabled ? "text-amber-800" : "text-muted"}`}>
            {enabled ? "Test preference ON" : "Test preference OFF"}
          </span>
          {enabled ? (
            <>
              <input
                className="min-h-10 rounded-xl border border-primary/15 px-3 py-2 text-sm"
                placeholder="Type LIVE to turn off"
                value={goLiveConfirm}
                onChange={(e) => setGoLiveConfirm(e.target.value)}
              />
              <Button
                size="sm"
                variant="outline"
                disabled={busy}
                onClick={() => void setPreference(false)}
              >
                Switch preference off
              </Button>
            </>
          ) : (
            <Button size="sm" disabled={busy} onClick={() => void setPreference(true)}>
              Turn test preference on
            </Button>
          )}
        </div>
      </section>

      <section className="rounded-2xl border border-primary/10 bg-white p-6">
        <h2 className="font-semibold text-primary">API console</h2>
        <p className="mt-2 text-sm text-muted">
          Run Partner-style actions without a raw key. Create booking always uses sandbox.
        </p>
        <div className="mt-4 flex flex-wrap gap-2">
          <select
            className="min-h-10 rounded-xl border border-primary/15 px-3 py-2 text-sm"
            value={consoleAction}
            onChange={(e) => setConsoleAction(e.target.value)}
          >
            <option value="list_orders">list_orders</option>
            <option value="create_booking">create_booking (sandbox)</option>
            <option value="simulate_lifecycle">simulate_lifecycle</option>
          </select>
          {consoleAction === "simulate_lifecycle" ? (
            <input
              className="min-h-10 min-w-[14rem] rounded-xl border border-primary/15 px-3 py-2 text-sm"
              placeholder="Sandbox order id"
              value={simOrderId}
              onChange={(e) => setSimOrderId(e.target.value)}
            />
          ) : null}
          <Button size="sm" disabled={busy} onClick={() => void runConsole()}>
            Run
          </Button>
        </div>
        {consoleOut ? (
          <pre className="mt-3 max-h-64 overflow-auto rounded-xl bg-gray-bg p-3 text-xs">
            {consoleOut}
          </pre>
        ) : null}
      </section>

      <section className="rounded-2xl border border-amber-200 bg-amber-50/40 p-6">
        <h2 className="font-semibold text-primary">Purge test orders</h2>
        <p className="mt-2 text-sm text-muted">
          Cancels undispatched sandbox orders for this company. Type{" "}
          <code className="rounded bg-white px-1">PURGE TEST</code> to confirm.
        </p>
        <div className="mt-4 flex flex-wrap gap-2">
          <input
            className="min-h-10 rounded-xl border border-primary/15 px-3 py-2 text-sm"
            value={purgeConfirm}
            onChange={(e) => setPurgeConfirm(e.target.value)}
            placeholder="PURGE TEST"
          />
          <Button size="sm" variant="outline" disabled={busy} onClick={() => void purge()}>
            Purge
          </Button>
        </div>
      </section>

      {note ? <p className="text-sm text-muted">{note}</p> : null}
    </div>
  );
}

function DocsTab({ docs }: { docs: ApiDoc }) {
  return (
    <div className="space-y-6">
      <section className="rounded-2xl border border-primary/10 bg-white p-6 text-sm">
        <h2 className="font-semibold text-primary">Authentication</h2>
        <p className="mt-2 text-muted">{docs.auth_note}</p>
        <p className="mt-2">
          Base URL: <code className="rounded bg-gray-bg px-1">{docs.base_url}/v1/merchant-api</code>
        </p>
        <p className="mt-2">
          Header:{" "}
          <code className="rounded bg-gray-bg px-1">{docs.auth_header}: &lt;your_key&gt;</code>
        </p>
        <p className="mt-2 text-muted">
          Default rate limit: {docs.default_rate_limit_per_minute} req/min · Scopes:{" "}
          {docs.default_scopes.join(", ")}
        </p>
      </section>
      <section className="rounded-2xl border border-primary/10 bg-white p-6">
        <h2 className="font-semibold text-primary">Endpoints</h2>
        <table className="mt-4 w-full text-sm">
          <thead className="text-left text-muted">
            <tr>
              <th className="pb-2">Method</th>
              <th className="pb-2">Path</th>
              <th className="pb-2">Scope</th>
              <th className="pb-2">What it does</th>
            </tr>
          </thead>
          <tbody>
            {docs.endpoints.map((ep) => (
              <tr key={`${ep.method}-${ep.path}`} className="border-t border-primary/5">
                <td className="py-2 font-mono text-xs">{ep.method}</td>
                <td className="py-2 font-mono text-xs">{ep.path}</td>
                <td className="py-2 text-muted">{ep.scope}</td>
                <td className="py-2 text-muted">{ep.description}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
      <section className="rounded-2xl border border-primary/10 bg-white p-6 text-sm">
        <h2 className="font-semibold text-primary">Webhook signatures</h2>
        <p className="mt-2 text-muted">
          Verify HMAC SHA-256 using headers{" "}
          <code className="rounded bg-gray-bg px-1">{docs.webhook_signature_header}</code> and{" "}
          <code className="rounded bg-gray-bg px-1">{docs.webhook_timestamp_header}</code>.
        </p>
      </section>
    </div>
  );
}

function DeliveryTable({
  rows,
  onRetry,
  compact,
}: {
  rows: WebhookDelivery[];
  onRetry?: (id: string) => void;
  compact?: boolean;
}) {
  if (rows.length === 0) {
    return <p className="text-sm text-muted">No webhook deliveries yet</p>;
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="text-left text-muted">
          <tr>
            <th className="px-2 py-2">Event</th>
            {!compact && <th className="px-2 py-2">Status</th>}
            <th className="px-2 py-2">HTTP</th>
            <th className="px-2 py-2">Attempt</th>
            <th className="px-2 py-2">Time</th>
            {onRetry && <th className="px-2 py-2" />}
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.id} className="border-t border-primary/5">
              <td className="px-2 py-2 font-mono text-xs">{r.event_type}</td>
              {!compact && (
                <td className="px-2 py-2">
                  <span className={r.success ? "text-green-700" : "text-red-600"}>
                    {r.success ? "OK" : "Failed"}
                  </span>
                </td>
              )}
              <td className="px-2 py-2">{r.response_status ?? "—"}</td>
              <td className="px-2 py-2">{r.attempt}</td>
              <td className="px-2 py-2 text-xs text-muted">
                {r.created_at ? formatDate(r.created_at) : "—"}
              </td>
              {onRetry && !r.success && (
                <td className="px-2 py-2">
                  <button
                    type="button"
                    className="text-xs text-primary underline"
                    onClick={() => onRetry(r.id)}
                  >
                    Retry
                  </button>
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function SecretBanner({
  secret,
  label,
  onDismiss,
}: {
  secret: string;
  label: string;
  onDismiss: () => void;
}) {
  return (
    <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm">
      <p className="font-semibold text-amber-900">
        Copy your {label} now — it won&apos;t be shown again
      </p>
      <code className="mt-2 block break-all rounded bg-white p-2 font-mono text-xs">{secret}</code>
      <div className="mt-2 flex gap-3">
        <button
          type="button"
          className="text-xs text-secondary underline"
          onClick={() => void navigator.clipboard.writeText(secret)}
        >
          Copy
        </button>
        <button type="button" className="text-xs text-muted underline" onClick={onDismiss}>
          Dismiss
        </button>
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-primary/10 bg-white p-5">
      <p className="text-sm text-muted">{label}</p>
      <p className="mt-2 text-2xl font-bold text-primary">{value}</p>
    </div>
  );
}
