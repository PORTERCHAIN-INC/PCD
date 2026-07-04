"use client";

import { useState } from "react";
import { Bell, RefreshCw, Send, Smartphone, FileText, AlertTriangle, Layers } from "lucide-react";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { useApiData } from "@/hooks/useApiData";
import { notificationsApi, type NotificationRecord } from "@/lib/notifications";
import { Badge, Button, EmptyState, SectionCard, Spinner } from "@/components/crm/primitives";
import { shortDate, titleCase } from "@/lib/crmFormat";

type Tab = "dashboard" | "queue" | "history" | "failed" | "templates" | "devices";

const STATUS_TONE: Record<string, string> = {
  queued: "amber",
  sent: "sky",
  delivered: "green",
  failed: "red",
  dead_letter: "red",
};

export default function NotificationsPage() {
  const { getApiToken } = useAdminAuth();
  const [tab, setTab] = useState<Tab>("dashboard");
  const [version, setVersion] = useState(0);
  const [search, setSearch] = useState("");
  const [busy, setBusy] = useState<string | null>(null);

  const { data: dashboard } = useApiData((t) => notificationsApi.dashboard(t), [version]);
  const { data: queue } = useApiData(
    (t) => (tab === "queue" ? notificationsApi.queue(t, search ? { search } : {}) : Promise.resolve([])),
    [tab, version, search]
  );
  const { data: history } = useApiData(
    (t) => (tab === "history" ? notificationsApi.history(t, search ? { search } : {}) : Promise.resolve([])),
    [tab, version, search]
  );
  const { data: failed } = useApiData(
    (t) => (tab === "failed" ? notificationsApi.failed(t) : Promise.resolve([])),
    [tab, version]
  );
  const { data: templates } = useApiData(
    (t) => (tab === "templates" ? notificationsApi.templates(t) : Promise.resolve([])),
    [tab, version]
  );
  const { data: devices } = useApiData(
    (t) => (tab === "devices" ? notificationsApi.devices(t) : Promise.resolve([])),
    [tab, version]
  );

  async function retry(id: string) {
    setBusy(id);
    try {
      const token = await getApiToken();
      await notificationsApi.retry(token, id);
      setVersion((v) => v + 1);
    } finally {
      setBusy(null);
    }
  }

  const tabs: { id: Tab; label: string; icon: React.ComponentType<{ className?: string }> }[] = [
    { id: "dashboard", label: "Dashboard", icon: Layers },
    { id: "queue", label: "Queue", icon: Send },
    { id: "history", label: "History", icon: Bell },
    { id: "failed", label: "Failed", icon: AlertTriangle },
    { id: "templates", label: "Templates", icon: FileText },
    { id: "devices", label: "Devices", icon: Smartphone },
  ];

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-bold text-primary">Notification Center</h1>
        <p className="text-sm text-muted">
          Enterprise notification engine — queue, delivery, templates, and device tokens.
        </p>
      </div>

      <div className="flex flex-wrap gap-2">
        {tabs.map(({ id, label, icon: Icon }) => (
          <Button
            key={id}
            variant={tab === id ? "primary" : "outline"}
            onClick={() => setTab(id)}
            className="gap-2"
          >
            <Icon className="h-4 w-4" /> {label}
          </Button>
        ))}
      </div>

      {(tab === "queue" || tab === "history") && (
        <input
          type="search"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search recipient, template, title…"
          className="w-full max-w-md rounded-xl border border-primary/15 px-3 py-2 text-sm"
        />
      )}

      {tab === "dashboard" && dashboard && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
          <Stat label="Total sent" value={dashboard.total} />
          <Stat label="Queued" value={dashboard.queued} accent="text-amber-600" />
          <Stat label="Failed" value={dashboard.failed} accent="text-red-600" />
          <Stat label="Active devices" value={dashboard.active_devices} accent="text-secondary" />
          <Stat label="Templates" value={dashboard.templates} />
        </div>
      )}

      {tab === "queue" && (
        <RecordTable rows={queue ?? undefined} onRetry={retry} busy={busy} empty="Queue is empty." />
      )}
      {tab === "history" && (
        <RecordTable rows={history ?? undefined} onRetry={retry} busy={busy} empty="No notification history yet." />
      )}
      {tab === "failed" && (
        <RecordTable rows={failed ?? undefined} onRetry={retry} busy={busy} empty="No failed notifications." showRetry />
      )}

      {tab === "templates" && (
        <SectionCard title={`Templates (${templates?.length ?? 0})`}>
          {!templates ? (
            <Spinner />
          ) : (
            <div className="divide-y divide-primary/5">
              {templates.map((t) => (
                <div key={t.key} className="flex items-center justify-between px-5 py-3">
                  <div>
                    <p className="text-sm font-medium text-primary">{t.key}</p>
                    <p className="text-xs text-muted">{t.subject}</p>
                  </div>
                  <Badge tone="slate">{titleCase(t.category)}</Badge>
                </div>
              ))}
            </div>
          )}
        </SectionCard>
      )}

      {tab === "devices" && (
        <SectionCard title={`Device tokens (${devices?.length ?? 0})`}>
          {!devices ? (
            <Spinner />
          ) : devices.length === 0 ? (
            <EmptyState title="No registered devices" hint="Devices register via POST /v1/notifications/devices/register" />
          ) : (
            <div className="divide-y divide-primary/5">
              {devices.map((d) => (
                <div key={d.id} className="flex items-center justify-between px-5 py-3">
                  <div>
                    <p className="text-sm font-medium text-primary">
                      {d.device_name ?? d.platform} · {titleCase(d.user_role)}
                    </p>
                    <p className="text-xs text-muted">
                      {d.user_id.slice(0, 8)}… · {d.app_version ?? "—"} · Last seen{" "}
                      {d.last_seen_at ? shortDate(d.last_seen_at) : "—"}
                    </p>
                  </div>
                  <Badge tone="green">{titleCase(d.platform)}</Badge>
                </div>
              ))}
            </div>
          )}
        </SectionCard>
      )}
    </div>
  );
}

function Stat({ label, value, accent = "text-primary" }: { label: string; value: number; accent?: string }) {
  return (
    <div className="rounded-2xl border border-primary/10 bg-white p-4 shadow-sm">
      <p className="text-xs text-muted">{label}</p>
      <p className={`mt-1 text-2xl font-bold ${accent}`}>{value.toLocaleString()}</p>
    </div>
  );
}

function RecordTable({
  rows,
  onRetry,
  busy,
  empty,
  showRetry = false,
}: {
  rows: NotificationRecord[] | undefined;
  onRetry: (id: string) => void;
  busy: string | null;
  empty: string;
  showRetry?: boolean;
}) {
  if (!rows) return <Spinner />;
  if (rows.length === 0) return <EmptyState title={empty} />;
  return (
    <SectionCard title={`Notifications (${rows.length})`}>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-primary/10 bg-gray-bg/40 text-xs uppercase text-muted">
            <tr>
              <th className="px-4 py-2">Title</th>
              <th className="px-4 py-2">Channel</th>
              <th className="px-4 py-2">Recipient</th>
              <th className="px-4 py-2">Status</th>
              <th className="px-4 py-2">Created</th>
              {showRetry && <th className="px-4 py-2" />}
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id} className="border-b border-primary/5">
                <td className="px-4 py-2">
                  <p className="font-medium text-primary">{r.title}</p>
                  <p className="text-xs text-muted">{r.template_key}</p>
                </td>
                <td className="px-4 py-2">{titleCase(r.channel)}</td>
                <td className="px-4 py-2 text-xs">
                  {titleCase(r.recipient_type)} · {r.recipient_id.slice(0, 8)}…
                </td>
                <td className="px-4 py-2">
                  <Badge tone={STATUS_TONE[r.status] ?? "slate"}>{titleCase(r.status)}</Badge>
                </td>
                <td className="px-4 py-2">{shortDate(r.created_at)}</td>
                {showRetry && (
                  <td className="px-4 py-2">
                    <Button
                      variant="outline"
                      className="px-2 py-1 text-xs"
                      disabled={busy === r.id}
                      onClick={() => onRetry(r.id)}
                    >
                      <RefreshCw className="h-3 w-3" /> Retry
                    </Button>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </SectionCard>
  );
}
