"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import {
  Bell,
  Camera,
  CloudOff,
  MapPin,
  RefreshCw,
  Smartphone,
  Wifi,
  WifiOff,
} from "lucide-react";
import DriverShell from "@/components/DriverShell";
import { useDriverCommunications } from "@/hooks/useDriverCommunications";
import { hasDriverSession } from "@/lib/api";
import { formatCommTime, groupLabel } from "@/lib/communications";
import { cn } from "@/lib/utils";

export default function CommunicationsPage() {
  const router = useRouter();
  const {
    data,
    error,
    loading,
    refreshing,
    syncing,
    wsConnected,
    refresh,
    syncOffline,
    markRead,
    registerPush,
  } = useDriverCommunications();

  useEffect(() => {
    hasDriverSession().then((ok) => {
      if (!ok) router.replace("/login");
    });
  }, [router]);

  if (loading && !data) {
    return (
      <DriverShell>
        <div className="animate-pulse space-y-4">
          <div className="h-10 w-48 rounded-xl bg-white" />
          <div className="h-32 rounded-2xl bg-white" />
        </div>
      </DriverShell>
    );
  }

  const snap = data!;

  return (
    <DriverShell>
      <header className="flex flex-col gap-3 border-b border-[var(--primary)]/8 pb-6 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold">Communications</h1>
          <p className="mt-1 text-sm text-[var(--muted)]">
            Push, realtime inbox, and offline sync — Notification Engine
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => syncOffline()}
            disabled={syncing}
            className="inline-flex items-center gap-2 rounded-xl border border-[var(--primary)]/10 bg-white px-4 py-2 text-sm font-medium"
          >
            <CloudOff className={cn("h-4 w-4", syncing && "animate-pulse")} />
            {syncing ? "Syncing…" : "Sync offline"}
          </button>
          <button
            type="button"
            onClick={refresh}
            disabled={refreshing}
            className="inline-flex items-center gap-2 rounded-xl border border-[var(--primary)]/10 bg-white px-4 py-2 text-sm font-medium"
          >
            <RefreshCw className={cn("h-4 w-4", refreshing && "animate-spin")} />
            Refresh
          </button>
        </div>
      </header>

      {error && (
        <p className="mt-4 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>
      )}

      <section className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Unread"
          value={String(snap.notifications.unread_count)}
          icon={Bell}
        />
        <StatCard
          label="Push devices"
          value={String(snap.push.registered_devices)}
          hint={snap.push.fcm_configured ? "Firebase configured" : "FCM pending config"}
          icon={Smartphone}
        />
        <StatCard
          label="Offline queue"
          value={String(snap.offline.pending_count)}
          hint={`${snap.offline.failed_count} failed`}
          icon={CloudOff}
        />
        <StatCard
          label="Realtime"
          value={wsConnected ? "Live" : "Polling"}
          hint={wsConnected ? "WebSocket connected" : "15s poll fallback"}
          icon={wsConnected ? Wifi : WifiOff}
        />
      </section>

      <section className="mt-8 rounded-2xl bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-lg font-bold">Firebase Push</h2>
          <button
            type="button"
            onClick={() => registerPush()}
            className="rounded-xl bg-[var(--primary)] px-4 py-2 text-sm font-semibold text-white"
          >
            Enable browser notifications
          </button>
        </div>
        <p className="mt-2 text-sm text-[var(--muted)]">
          Registers this browser with the Notification Engine for assignment, route, emergency,
          support, and claims push alerts.
        </p>
        {snap.push.devices.length > 0 && (
          <ul className="mt-4 space-y-2 text-sm">
            {snap.push.devices.map((d) => (
              <li key={d.id} className="flex justify-between rounded-xl bg-[var(--gray-bg)] px-3 py-2">
                <span>
                  {d.platform} {d.device_name ? `· ${d.device_name}` : ""}
                </span>
                <span className="text-[var(--muted)]">{formatCommTime(d.last_seen_at)}</span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="mt-8 space-y-6">
        {Object.entries(snap.notifications.by_group).map(([group, items]) =>
          items.length > 0 ? (
            <div key={group} className="rounded-2xl bg-white p-5 shadow-sm">
              <h2 className="text-lg font-bold">{groupLabel(group)}</h2>
              <ul className="mt-4 space-y-2">
                {items.map((n) => (
                  <li
                    key={n.id}
                    className={cn(
                      "rounded-xl px-4 py-3 text-sm",
                      n.is_read ? "bg-[var(--gray-bg)]" : "bg-[var(--secondary)]/10"
                    )}
                  >
                    <div className="flex justify-between gap-2">
                      <p className="font-semibold">{n.title}</p>
                      {!n.is_read && (
                        <button
                          type="button"
                          onClick={() => markRead(n.id)}
                          className="text-xs font-semibold text-[var(--secondary)]"
                        >
                          Mark read
                        </button>
                      )}
                    </div>
                    <p className="mt-1 text-[var(--muted)]">{n.body}</p>
                    <p className="mt-1 text-xs text-[var(--muted)]">{formatCommTime(n.created_at)}</p>
                  </li>
                ))}
              </ul>
            </div>
          ) : null
        )}
      </section>

      <section className="mt-8 grid gap-4 lg:grid-cols-2">
        <div className="rounded-2xl bg-white p-5 shadow-sm">
          <div className="flex items-center gap-2">
            <MapPin className="h-5 w-5 text-[var(--secondary)]" />
            <h2 className="text-lg font-bold">GPS Recovery</h2>
          </div>
          <p className="mt-2 text-sm text-[var(--muted)]">
            Location pings buffered offline sync automatically when connectivity returns.
          </p>
          <p className="mt-3 text-2xl font-bold">{snap.offline.gps_pending} pending</p>
        </div>
        <div className="rounded-2xl bg-white p-5 shadow-sm">
          <div className="flex items-center gap-2">
            <Camera className="h-5 w-5 text-[var(--secondary)]" />
            <h2 className="text-lg font-bold">Camera Upload Queue</h2>
          </div>
          <p className="mt-2 text-sm text-[var(--muted)]">
            POD photos and document uploads retry from the offline queue.
          </p>
          <p className="mt-3 text-2xl font-bold">{snap.offline.camera_upload_pending} pending</p>
          {snap.offline.failed_uploads > 0 && (
            <p className="mt-1 text-sm text-red-700">{snap.offline.failed_uploads} failed — use Sync offline</p>
          )}
        </div>
      </section>

      {snap.offline.failed.length > 0 && (
        <section className="mt-8 rounded-2xl bg-white p-5 shadow-sm">
          <h2 className="text-lg font-bold">Failed uploads / actions</h2>
          <ul className="mt-4 space-y-2">
            {snap.offline.failed.map((row) => (
              <li key={row.id} className="rounded-xl bg-red-50 px-4 py-3 text-sm">
                <p className="font-semibold capitalize">{row.action_type.replace(/_/g, " ")}</p>
                <p className="text-xs text-red-800">{row.error}</p>
              </li>
            ))}
          </ul>
        </section>
      )}

      <p className="mt-6 text-xs text-[var(--muted)]">
        Last synced {new Date(snap.last_updated).toLocaleString()}
        {snap.offline.last_sync_at ? ` · Offline sync ${formatCommTime(snap.offline.last_sync_at)}` : ""}
      </p>
    </DriverShell>
  );
}

function StatCard({
  label,
  value,
  hint,
  icon: Icon,
}: {
  label: string;
  value: string;
  hint?: string;
  icon: React.ComponentType<{ className?: string }>;
}) {
  return (
    <div className="rounded-2xl bg-white p-5 shadow-sm">
      <div className="flex items-center gap-2">
        <Icon className="h-4 w-4 text-[var(--secondary)]" />
        <p className="text-sm text-[var(--muted)]">{label}</p>
      </div>
      <p className="mt-2 text-2xl font-bold">{value}</p>
      {hint && <p className="mt-1 text-xs text-[var(--muted)]">{hint}</p>}
    </div>
  );
}
