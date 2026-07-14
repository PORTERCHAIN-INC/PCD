"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import {
  Bell,
  RefreshCw,
  Send,
  Smartphone,
  FileText,
  AlertTriangle,
  Layers,
  Inbox,
} from "lucide-react";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { useApiData } from "@/hooks/useApiData";
import {
  notificationsApi,
  type InboxNotification,
  type NotificationRecord,
} from "@/lib/notifications";
import { Badge, Button, EmptyState, SectionCard, Spinner } from "@/components/crm/primitives";
import { shortDate, titleCase } from "@/lib/crmFormat";
import { cn } from "@porterchain/ui/utils";

type Tab = "inbox" | "dashboard" | "queue" | "history" | "failed" | "templates" | "devices";

const STATUS_TONE: Record<string, string> = {
  queued: "amber",
  sent: "sky",
  delivered: "green",
  failed: "red",
  dead_letter: "red",
};

const TAB_IDS = new Set<Tab>([
  "inbox",
  "dashboard",
  "queue",
  "history",
  "failed",
  "templates",
  "devices",
]);

export default function NotificationsPage() {
  const searchParams = useSearchParams();
  const { getApiToken } = useAdminAuth();
  const initial = searchParams.get("tab");
  const [tab, setTab] = useState<Tab>(
    initial && TAB_IDS.has(initial as Tab) ? (initial as Tab) : "inbox"
  );
  const [version, setVersion] = useState(0);
  const [search, setSearch] = useState("");
  const [busy, setBusy] = useState<string | null>(null);

  useEffect(() => {
    const q = searchParams.get("tab");
    if (q && TAB_IDS.has(q as Tab)) setTab(q as Tab);
  }, [searchParams]);

  const { data: inbox } = useApiData(
    (t) => (tab === "inbox" ? notificationsApi.inbox(t) : Promise.resolve(null)),
    [tab, version]
  );
  const { data: dashboard } = useApiData(
    (t) => (tab === "dashboard" ? notificationsApi.dashboard(t) : Promise.resolve(null)),
    [tab, version]
  );
  const { data: queue } = useApiData(
    (t) =>
      tab === "queue" ? notificationsApi.queue(t, search ? { search } : {}) : Promise.resolve([]),
    [tab, version, search]
  );
  const { data: history } = useApiData(
    (t) =>
      tab === "history"
        ? notificationsApi.history(t, search ? { search } : {})
        : Promise.resolve([]),
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

  async function markRead(id: string) {
    setBusy(id);
    try {
      const token = await getApiToken();
      await notificationsApi.markRead(token, id);
      setVersion((v) => v + 1);
    } finally {
      setBusy(null);
    }
  }

  async function markAllRead() {
    setBusy("all");
    try {
      const token = await getApiToken();
      await notificationsApi.markAllRead(token);
      setVersion((v) => v + 1);
    } finally {
      setBusy(null);
    }
  }

  const tabs: { id: Tab; label: string; icon: React.ComponentType<{ className?: string }> }[] = [
    { id: "inbox", label: "My alerts", icon: Inbox },
    { id: "dashboard", label: "Dashboard", icon: Layers },
    { id: "queue", label: "Queue", icon: Send },
    { id: "history", label: "History", icon: Bell },
    { id: "failed", label: "Failed", icon: AlertTriangle },
    { id: "templates", label: "Templates", icon: FileText },
    { id: "devices", label: "Devices", icon: Smartphone },
  ];

  const unread = inbox?.unread_count ?? 0;

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-primary">Notification Center</h1>
          <p className="text-sm text-muted">
            Your alerts, plus delivery queue, templates, and devices.
          </p>
        </div>
        {tab === "inbox" && unread > 0 ? (
          <Button variant="outline" disabled={busy === "all"} onClick={() => void markAllRead()}>
            Mark all read
          </Button>
        ) : null}
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
            {id === "inbox" && unread > 0 ? (
              <span className="rounded-full bg-white/20 px-1.5 text-[10px] font-bold">
                {unread}
              </span>
            ) : null}
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

      {tab === "inbox" && (
        <InboxPanel
          data={inbox}
          busy={busy}
          onOpen={(item) => {
            if (!item.is_read) void markRead(item.id);
            if (item.deep_link) window.location.href = item.deep_link;
          }}
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
        <RecordTable
          rows={queue ?? undefined}
          onRetry={retry}
          busy={busy}
          empty="Queue is empty."
        />
      )}
      {tab === "history" && (
        <RecordTable
          rows={history ?? undefined}
          onRetry={retry}
          busy={busy}
          empty="No notification history yet."
        />
      )}
      {tab === "failed" && (
        <RecordTable
          rows={failed ?? undefined}
          onRetry={retry}
          busy={busy}
          empty="No failed notifications."
          showRetry
        />
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
            <EmptyState
              title="No registered devices"
              hint="Devices register via POST /v1/notifications/devices/register"
            />
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

function InboxPanel({
  data,
  busy,
  onOpen,
}: {
  data: { unread_count: number; items: InboxNotification[] } | null | undefined;
  busy: string | null;
  onOpen: (item: InboxNotification) => void;
}) {
  if (!data) return <Spinner label="Loading alerts…" />;
  if (data.items.length === 0) {
    return <EmptyState title="No alerts yet" hint="You’re all caught up." />;
  }
  return (
    <SectionCard title={`My alerts (${data.unread_count} unread)`}>
      <ul className="divide-y divide-primary/5">
        {data.items.map((n) => (
          <li key={n.id}>
            <button
              type="button"
              disabled={busy === n.id}
              onClick={() => onOpen(n)}
              className={cn(
                "flex w-full flex-col gap-1 px-5 py-3.5 text-left transition hover:bg-gray-bg/80",
                !n.is_read && "bg-secondary/5"
              )}
            >
              <span className="flex items-center justify-between gap-2">
                <span className="font-medium text-primary">{n.title || "Update"}</span>
                <span className="flex items-center gap-2">
                  {!n.is_read ? <Badge tone="sky">New</Badge> : null}
                  <span className="text-xs text-muted">{shortDate(n.created_at)}</span>
                </span>
              </span>
              <span className="text-sm text-muted">{n.body}</span>
            </button>
          </li>
        ))}
      </ul>
    </SectionCard>
  );
}

function Stat({
  label,
  value,
  accent = "text-primary",
}: {
  label: string;
  value: number;
  accent?: string;
}) {
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
