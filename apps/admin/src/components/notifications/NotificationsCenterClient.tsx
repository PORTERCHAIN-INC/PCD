"use client";

import { useEffect, useState, Fragment } from "react";
import { PageSkeleton } from "@porterchain/ui/loading";
import { useSearchParams } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
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
import { Badge, Button, EmptyState, SectionCard } from "@/components/crm/primitives";
import { shortDate, titleCase } from "@/lib/crmFormat";
import { cn } from "@porterchain/ui/utils";
import AdminPage from "@/components/layout/AdminPage";

/** Bell cache. This page uses its own key so lead pointers stay off the center. */
const BELL_INBOX_KEY = ["admin-notification-inbox"] as const;
const CENTER_INBOX_KEY = ["admin-notification-center-inbox"] as const;
const LEAD_NOTICE = "lead_sla_escalation";

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

export default function NotificationsCenterClient() {
  const searchParams = useSearchParams();
  const { getApiToken, isLoaded, isSignedIn } = useAdminAuth();
  const qc = useQueryClient();
  const initial = searchParams.get("tab");
  const [tab, setTab] = useState<Tab>(
    initial && TAB_IDS.has(initial as Tab) ? (initial as Tab) : "inbox"
  );
  const [version, setVersion] = useState(0);
  const [search, setSearch] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [testEmail, setTestEmail] = useState("");
  const [testMsg, setTestMsg] = useState<string | null>(null);

  useEffect(() => {
    const q = searchParams.get("tab");
    if (q && TAB_IDS.has(q as Tab)) setTab(q as Tab);
  }, [searchParams]);

  const authOk = isLoaded && (isSignedIn || process.env.NODE_ENV === "development");
  const { data: inbox } = useQuery({
    queryKey: CENTER_INBOX_KEY,
    enabled: authOk && tab === "inbox",
    queryFn: async () => notificationsApi.inbox(await getApiToken(), 100, LEAD_NOTICE),
  });
  const { data: dashboard } = useApiData((t) => notificationsApi.dashboard(t), [version], {
    key: "notifications-dashboard",
    enabled: tab === "dashboard",
  });
  const { data: queue } = useApiData(
    (t) => notificationsApi.queue(t, search ? { search } : {}),
    [version, search],
    { key: "notifications-queue", enabled: tab === "queue" }
  );
  const { data: history } = useApiData(
    (t) => notificationsApi.history(t, search ? { search } : {}),
    [version, search],
    { key: "notifications-history", enabled: tab === "history" }
  );
  const { data: failed } = useApiData((t) => notificationsApi.failed(t), [version], {
    key: "notifications-failed",
    enabled: tab === "failed",
  });
  const { data: templates } = useApiData((t) => notificationsApi.templates(t), [version], {
    key: "notifications-templates",
    enabled: tab === "templates",
  });
  const { data: devices } = useApiData((t) => notificationsApi.devices(t), [version], {
    key: "notifications-devices",
    enabled: tab === "devices",
  });

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
      await qc.invalidateQueries({ queryKey: CENTER_INBOX_KEY });
      await qc.invalidateQueries({ queryKey: BELL_INBOX_KEY });
    } finally {
      setBusy(null);
    }
  }

  async function markAllRead() {
    setBusy("all");
    try {
      const token = await getApiToken();
      await notificationsApi.markAllRead(token);
      await qc.invalidateQueries({ queryKey: CENTER_INBOX_KEY });
      await qc.invalidateQueries({ queryKey: BELL_INBOX_KEY });
    } finally {
      setBusy(null);
    }
  }

  async function sendTest(templateKey: string) {
    setBusy(templateKey);
    setTestMsg(null);
    try {
      const token = await getApiToken();
      const result = await notificationsApi.sendTest(token, {
        template_key: templateKey,
        channel: "email",
        recipient_address: testEmail.trim() || undefined,
      });
      setTestMsg(
        result.ok
          ? `Sent ${templateKey} → ${result.status} (${result.notification_id?.slice(0, 8) ?? "—"}…)`
          : "Send test failed"
      );
      setVersion((v) => v + 1);
    } catch (e) {
      setTestMsg(e instanceof Error ? e.message : "Send test failed");
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
    <AdminPage>
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

      {tab === "dashboard" && dashboard && !Array.isArray(dashboard) && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
          <Stat label="Total sent" value={dashboard.total ?? 0} />
          <Stat label="Queued" value={dashboard.queued ?? 0} accent="text-amber-600" />
          <Stat label="Failed" value={dashboard.failed ?? 0} accent="text-red-600" />
          <Stat
            label="Active devices"
            value={dashboard.active_devices ?? 0}
            accent="text-secondary"
          />
          <Stat label="Templates" value={dashboard.templates ?? 0} />
        </div>
      )}

      {tab === "queue" && (
        <RecordTable
          rows={withoutLeadNotices(queue ?? undefined)}
          onRetry={retry}
          busy={busy}
          empty="Queue is empty."
        />
      )}
      {tab === "history" && (
        <RecordTable
          rows={withoutLeadNotices(history ?? undefined)}
          onRetry={retry}
          busy={busy}
          empty="No notification history yet."
        />
      )}
      {tab === "failed" && (
        <RecordTable
          rows={withoutLeadNotices(failed ?? undefined)}
          onRetry={retry}
          busy={busy}
          empty="No failed notifications."
          showRetry
        />
      )}

      {tab === "templates" && (
        <SectionCard title={`Templates (${templates?.length ?? 0})`}>
          <div className="flex flex-wrap items-end gap-3 border-b border-primary/8 px-5 py-3">
            <label className="flex min-w-[220px] flex-1 flex-col gap-1 text-xs text-muted">
              Send-test email (Mailpit / SMTP)
              <input
                type="email"
                value={testEmail}
                onChange={(e) => setTestEmail(e.target.value)}
                placeholder="you@porterchain.com"
                className="rounded-lg border border-primary/15 px-3 py-2 text-sm text-primary"
              />
            </label>
            {testMsg ? <p className="text-xs text-muted">{testMsg}</p> : null}
          </div>
          {!templates ? (
            <PageSkeleton rows={3} />
          ) : (
            <div className="divide-y divide-primary/5">
              {templates.map((t) => (
                <div key={t.key} className="flex items-center justify-between gap-3 px-5 py-3">
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-primary">{t.key}</p>
                    <p className="truncate text-xs text-muted">{t.subject}</p>
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    <Badge tone="slate">{titleCase(t.category)}</Badge>
                    <Button
                      variant="outline"
                      disabled={busy === t.key}
                      onClick={() => void sendTest(t.key)}
                      className="gap-1.5 text-xs"
                    >
                      <Send className="h-3.5 w-3.5" />
                      Send test
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </SectionCard>
      )}

      {tab === "devices" && (
        <SectionCard title={`Device tokens (${devices?.length ?? 0})`}>
          <div className="flex flex-wrap items-center gap-2 border-b border-primary/5 px-5 py-3">
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                void (async () => {
                  const { registerBrowserPush } = await import("@/lib/web-push");
                  const ok = await registerBrowserPush(getApiToken);
                  if (ok) window.location.reload();
                  else
                    window.alert(
                      "Browser push not enabled (permission, Firebase config, or token)."
                    );
                })();
              }}
            >
              Enable browser push
            </Button>
            <p className="text-xs text-muted">
              Registers this admin browser via FCM → /v1/notifications/devices/register
            </p>
          </div>
          {!devices ? (
            <PageSkeleton rows={3} />
          ) : devices.length === 0 ? (
            <EmptyState
              title="No registered devices"
              hint="Click Enable browser push above, or register via POST /v1/notifications/devices/register"
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
    </AdminPage>
  );
}

function withoutLeadNotices(rows: NotificationRecord[] | undefined) {
  return rows?.filter((row) => row.template_key !== LEAD_NOTICE);
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
  if (!data) {
    return (
      <div className="space-y-3 px-1 py-2" aria-hidden>
        <div className="h-4 w-40 animate-pulse rounded bg-primary/5 motion-reduce:animate-none" />
        <div className="h-16 w-full animate-pulse rounded-xl bg-primary/5 motion-reduce:animate-none" />
        <div className="h-16 w-full animate-pulse rounded-xl bg-primary/5 motion-reduce:animate-none" />
        <div className="h-16 w-full animate-pulse rounded-xl bg-primary/5 motion-reduce:animate-none" />
      </div>
    );
  }
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
  value: number | null | undefined;
  accent?: string;
}) {
  return (
    <div className="rounded-2xl border border-primary/10 bg-white p-4 shadow-sm">
      <p className="text-xs text-muted">{label}</p>
      <p className={`mt-1 text-2xl font-bold ${accent}`}>{(value ?? 0).toLocaleString()}</p>
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
  const { getApiToken } = useAdminAuth();
  const [expanded, setExpanded] = useState<string | null>(null);
  const [logs, setLogs] = useState<
    Record<
      string,
      Array<{
        id: string;
        channel: string;
        status: string;
        error: string | null;
        recipient: string;
        created_at: string | null;
      }>
    >
  >({});

  async function toggleReceipts(id: string) {
    if (expanded === id) {
      setExpanded(null);
      return;
    }
    setExpanded(id);
    if (!logs[id]) {
      const token = await getApiToken();
      const data = await notificationsApi.deliveryLogs(token, id);
      setLogs((prev) => ({ ...prev, [id]: data }));
    }
  }

  if (!rows) return <PageSkeleton rows={3} />;
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
              <th className="px-4 py-2">Receipts</th>
              {showRetry && <th className="px-4 py-2" />}
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <Fragment key={r.id}>
                <tr className="border-b border-primary/5">
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
                  <td className="px-4 py-2">
                    <button
                      type="button"
                      className="text-xs font-medium text-secondary hover:underline"
                      onClick={() => void toggleReceipts(r.id)}
                    >
                      {expanded === r.id ? "Hide" : "View"}
                    </button>
                  </td>
                  {showRetry ? (
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
                  ) : null}
                </tr>
                {expanded === r.id ? (
                  <tr className="bg-slate-50/80">
                    <td colSpan={showRetry ? 7 : 6} className="px-4 py-3">
                      {!logs[r.id] ? (
                        <PageSkeleton rows={3} />
                      ) : logs[r.id].length === 0 ? (
                        <p className="text-xs text-muted">No delivery attempts logged yet.</p>
                      ) : (
                        <ul className="space-y-1 text-xs text-muted">
                          {logs[r.id].map((log) => (
                            <li key={log.id}>
                              <span className="font-medium text-primary">
                                {titleCase(log.status)}
                              </span>
                              {" · "}
                              {titleCase(log.channel)} · {log.recipient || "—"}
                              {log.error ? ` · ${log.error}` : ""}
                              {log.created_at ? ` · ${shortDate(log.created_at)}` : ""}
                            </li>
                          ))}
                        </ul>
                      )}
                    </td>
                  </tr>
                ) : null}
              </Fragment>
            ))}
          </tbody>
        </table>
      </div>
    </SectionCard>
  );
}
