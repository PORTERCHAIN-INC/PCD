"use client";

import Button from "@/components/ui/Button";
import { useMerchantAuth } from "@/hooks/useMerchantAuth";
import {
  integrationsApi,
  WEBHOOK_EVENT_PRESETS,
  type ApiDoc,
  type ApiKeyRecord,
  type CsvTemplate,
  type ErpPlatform,
  type EventCatalogItem,
  type IntegrationsOverview,
  type OAuthProvider,
  type RateLimitRow,
  type WebhookDelivery,
  type WebhookRecord,
} from "@/lib/integrations";
import { formatDate } from "@/lib/utils";
import { useCallback, useEffect, useState } from "react";

type Tab =
  "overview" | "keys" | "webhooks" | "logs" | "usage" | "sandbox" | "docs" | "erp" | "console";

const TABS: { id: Tab; label: string }[] = [
  { id: "overview", label: "Overview" },
  { id: "keys", label: "API Keys" },
  { id: "webhooks", label: "Webhooks" },
  { id: "logs", label: "Webhook Logs" },
  { id: "usage", label: "API Usage" },
  { id: "sandbox", label: "Sandbox" },
  { id: "docs", label: "Documentation" },
  { id: "erp", label: "ERP" },
  { id: "console", label: "API Console" },
];

export default function IntegrationsClient() {
  const { getApiToken, orgId, isLoaded, isSignedIn } = useMerchantAuth();
  const [tab, setTab] = useState<Tab>("overview");
  const [overview, setOverview] = useState<IntegrationsOverview | null>(null);
  const [keys, setKeys] = useState<ApiKeyRecord[]>([]);
  const [webhooks, setWebhooks] = useState<WebhookRecord[]>([]);
  const [logs, setLogs] = useState<WebhookDelivery[]>([]);
  const [docs, setDocs] = useState<ApiDoc | null>(null);
  const [events, setEvents] = useState<EventCatalogItem[]>([]);
  const [erp, setErp] = useState<ErpPlatform[]>([]);
  const [oauth, setOauth] = useState<OAuthProvider[]>([]);
  const [templates, setTemplates] = useState<CsvTemplate[]>([]);
  const [limits, setLimits] = useState<RateLimitRow[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    if (!isSignedIn) return;
    setLoading(true);
    setError(null);
    try {
      const token = await getApiToken();
      const [ov, keyRows, hookRows, logRows, doc, ev, erpData, oauthData, tmpl, rateData] =
        await Promise.all([
          integrationsApi.overview(token, orgId),
          integrationsApi.listKeys(token, orgId),
          integrationsApi.listWebhooks(token, orgId),
          integrationsApi.webhookLogs(token, orgId),
          integrationsApi.documentation(token, orgId),
          integrationsApi.events(token, orgId),
          integrationsApi.erp(token, orgId),
          integrationsApi.oauth(token, orgId),
          integrationsApi.csvTemplates(token, orgId),
          integrationsApi.rateLimits(token, orgId),
        ]);
      setOverview(ov);
      setKeys(keyRows);
      setWebhooks(hookRows);
      setLogs(logRows);
      setDocs(doc);
      setEvents(ev.events);
      setErp(erpData.platforms);
      setOauth(oauthData.providers);
      setTemplates(tmpl.templates);
      setLimits(rateData.limits);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load integrations");
    } finally {
      setLoading(false);
    }
  }, [getApiToken, orgId, isSignedIn]);

  useEffect(() => {
    if (!isLoaded || !isSignedIn) return;
    void load();
  }, [isLoaded, isSignedIn, load]);

  if (!isLoaded || (loading && !overview)) {
    return <p className="text-muted">Loading integrations…</p>;
  }

  if (error && !overview) {
    return (
      <div className="space-y-4">
        <p className="text-red-600">{error}</p>
        <Button onClick={() => void load()}>Retry</Button>
      </div>
    );
  }

  if (!overview) return null;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-primary">Integrations</h1>
        <p className="mt-1 text-sm text-muted">
          API keys, webhooks, sandbox mode, usage analytics, and ERP readiness
        </p>
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <nav className="flex flex-wrap gap-2 border-b border-primary/10 pb-2">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setTab(t.id)}
            className={`rounded-lg px-3 py-1.5 text-sm font-medium transition ${
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
        <LogsTab
          logs={logs}
          webhooks={webhooks}
          onRefresh={load}
          getToken={getApiToken}
          orgId={orgId}
        />
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
      {tab === "docs" && docs && <DocsTab docs={docs} events={events} />}
      {tab === "erp" && (
        <ErpTab
          platforms={erp}
          oauth={oauth}
          templates={templates}
          getToken={getApiToken}
          orgId={orgId}
        />
      )}
      {tab === "console" && <ConsoleTab getToken={getApiToken} orgId={orgId} />}
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
        <Metric label="Sandbox" value={overview.sandbox_mode ? "Enabled" : "Disabled"} />
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
      <div className="flex flex-wrap gap-2">
        {overview.erp_platforms.map((p) => (
          <span
            key={p}
            className="rounded-full bg-green-50 px-3 py-1 text-xs font-medium text-green-800"
          >
            {p} ready
          </span>
        ))}
      </div>
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

  const updateLimit = async (keyId: string, value: number) => {
    const token = await getToken();
    await integrationsApi.updateRateLimit(token, keyId, value, orgId);
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
                  <input
                    type="number"
                    min={10}
                    max={600}
                    defaultValue={k.rate_limit_per_minute}
                    className="w-20 rounded border border-primary/15 px-2 py-1 text-xs"
                    onBlur={(e) => void updateLimit(k.id, Number(e.target.value))}
                  />
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
  const [newSecret, setNewSecret] = useState<string | null>(null);

  const toggleEvent = (ev: string) => {
    setSelectedEvents((prev) => (prev.includes(ev) ? prev.filter((e) => e !== ev) : [...prev, ev]));
  };

  const create = async (e: React.FormEvent) => {
    e.preventDefault();
    const token = await getToken();
    const row = await integrationsApi.createWebhook(token, { url, events: selectedEvents }, orgId);
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
              <p className="mt-1 text-xs text-muted">{h.events.join(", ") || "all events"}</p>
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
  webhooks,
  onRefresh,
  getToken,
  orgId,
}: {
  logs: WebhookDelivery[];
  webhooks: WebhookRecord[];
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
      <DeliveryTable rows={logs} webhooks={webhooks} onRetry={retry} />
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
  const toggle = async () => {
    const token = await getToken();
    await integrationsApi.setSandbox(token, !enabled, orgId);
    await onRefresh();
  };

  return (
    <section className="rounded-2xl border border-primary/10 bg-white p-6">
      <h2 className="font-semibold text-primary">Sandbox mode</h2>
      <p className="mt-2 text-sm text-muted">
        When enabled, use <code className="rounded bg-gray-bg px-1">pk_sandbox_</code> keys for safe
        integration testing. Production keys remain available but should only be used after go-live
        validation.
      </p>
      <div className="mt-4 flex items-center gap-4">
        <span className={`text-sm font-medium ${enabled ? "text-green-700" : "text-muted"}`}>
          {enabled ? "Sandbox enabled" : "Sandbox disabled"}
        </span>
        <Button size="sm" variant="outline" onClick={() => void toggle()}>
          {enabled ? "Disable" : "Enable"} sandbox
        </Button>
      </div>
    </section>
  );
}

function DocsTab({ docs, events }: { docs: ApiDoc; events: EventCatalogItem[] }) {
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
            </tr>
          </thead>
          <tbody>
            {docs.endpoints.map((ep) => (
              <tr key={ep.path} className="border-t border-primary/5">
                <td className="py-2 font-mono text-xs">{ep.method}</td>
                <td className="py-2 font-mono text-xs">{ep.path}</td>
                <td className="py-2 text-muted">{ep.scope}</td>
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

function ErpTab({
  platforms,
  oauth,
  templates,
  getToken,
  orgId,
}: {
  platforms: ErpPlatform[];
  oauth: OAuthProvider[];
  templates: CsvTemplate[];
  getToken: () => Promise<string>;
  orgId?: string;
}) {
  return (
    <div className="space-y-6">
      <div className="grid gap-4 lg:grid-cols-3">
        {platforms.map((p) => (
          <div key={p.id} className="rounded-2xl border border-primary/10 bg-white p-5">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold text-primary">{p.name}</h3>
              <span
                className={`rounded-full px-2 py-0.5 text-xs ${
                  p.status === "ready" ? "bg-green-50 text-green-800" : "bg-gray-100 text-muted"
                }`}
              >
                {p.status}
              </span>
            </div>
            <p className="mt-2 text-sm text-muted">{p.notes}</p>
            <p className="mt-2 text-xs text-muted">{p.capabilities.join(" · ")}</p>
          </div>
        ))}
      </div>
      <section className="rounded-2xl border border-primary/10 bg-white p-6">
        <h2 className="font-semibold text-primary">OAuth (future ready)</h2>
        <ul className="mt-4 space-y-2 text-sm">
          {oauth.map((p) => (
            <li key={p.id} className="flex justify-between gap-4">
              <span>{p.name}</span>
              <span className="text-muted">{p.status.replace("_", " ")}</span>
            </li>
          ))}
        </ul>
      </section>
      <section className="rounded-2xl border border-primary/10 bg-white p-6">
        <h2 className="font-semibold text-primary">CSV import templates</h2>
        <ul className="mt-4 space-y-3 text-sm">
          {templates.map((t) => (
            <li key={t.id} className="flex items-center justify-between gap-4">
              <div>
                <p className="font-medium">{t.name}</p>
                <p className="text-xs text-muted">{t.description}</p>
              </div>
              <Button
                size="sm"
                variant="outline"
                onClick={() =>
                  void getToken().then((token) =>
                    integrationsApi.downloadTemplate(token, t.id, orgId)
                  )
                }
              >
                Download CSV
              </Button>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}

function ConsoleTab({ getToken, orgId }: { getToken: () => Promise<string>; orgId?: string }) {
  const [action, setAction] = useState("list_orders");
  const [payload, setPayload] = useState('{"limit": 5}');
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const run = async () => {
    setError(null);
    try {
      const token = await getToken();
      const parsed = JSON.parse(payload) as Record<string, unknown>;
      const res = await integrationsApi.console(token, action, parsed, orgId);
      setResult(JSON.stringify(res, null, 2));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Console request failed");
      setResult(null);
    }
  };

  return (
    <section className="rounded-2xl border border-primary/10 bg-white p-6">
      <h2 className="font-semibold text-primary">API testing console</h2>
      <p className="mt-1 text-sm text-muted">
        Test merchant API actions via Clerk auth — no API key required in the browser.
      </p>
      <div className="mt-4 flex flex-wrap gap-3">
        <select
          className="rounded-lg border border-primary/15 px-3 py-2 text-sm"
          value={action}
          onChange={(e) => setAction(e.target.value)}
        >
          <option value="list_orders">list_orders</option>
          <option value="get_order">get_order</option>
          <option value="track">track</option>
          <option value="create_booking">create_booking</option>
        </select>
        <Button size="sm" onClick={() => void run()}>
          Run
        </Button>
      </div>
      <textarea
        className="mt-4 w-full rounded-xl border border-primary/15 p-3 font-mono text-xs"
        rows={6}
        value={payload}
        onChange={(e) => setPayload(e.target.value)}
      />
      {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
      {result && (
        <pre className="mt-4 overflow-x-auto rounded-xl bg-gray-bg p-4 text-xs">{result}</pre>
      )}
    </section>
  );
}

function DeliveryTable({
  rows,
  webhooks,
  onRetry,
  compact,
}: {
  rows: WebhookDelivery[];
  webhooks?: WebhookRecord[];
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
      <button type="button" className="mt-2 text-xs text-muted underline" onClick={onDismiss}>
        Dismiss
      </button>
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
