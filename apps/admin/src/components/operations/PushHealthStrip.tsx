"use client";

import Link from "next/link";
import { Bell, BellOff, CheckCircle2, Radio, Smartphone } from "lucide-react";
import { cn } from "@porterchain/ui/utils";
import { useApiData } from "@/hooks/useApiData";
import { notificationsApi, type PushHealth } from "@/lib/notifications";
import { relativeTime } from "@/lib/crmFormat";

const TONE: Record<PushHealth["tone"], { ring: string; label: string; icon: string }> = {
  ok: {
    ring: "border-green-200 bg-green-50/50",
    label: "text-green-800",
    icon: "text-green-600",
  },
  warn: {
    ring: "border-amber-200 bg-amber-50/60",
    label: "text-amber-900",
    icon: "text-amber-600",
  },
  danger: {
    ring: "border-red-200 bg-red-50/60",
    label: "text-red-900",
    icon: "text-red-600",
  },
};

/** Compact FCM / staff-device reach strip for Operations Control Tower. */
export function PushHealthStrip({
  tick = 0,
  compactWhenOk = true,
}: {
  tick?: number;
  /** When healthy, render a header chip instead of the full strip. */
  compactWhenOk?: boolean;
}) {
  const { data, error } = useApiData((t) => notificationsApi.pushHealth(t), [tick], {
    key: "ops-push-health",
  });

  if (error && !data) {
    return (
      <div
        className="flex items-center gap-2 rounded-xl border border-amber-200 bg-amber-50/50 px-3 py-2 text-xs text-amber-900"
        data-testid="ops-push-health"
      >
        <BellOff className="h-3.5 w-3.5 shrink-0" />
        Push health unavailable — check notifications/dispatch permission.
      </div>
    );
  }
  if (!data?.fcm || !data.devices || !data.critical_24h) return null;

  const tone = TONE[data.tone] ?? TONE.warn;
  const StatusIcon = data.tone === "ok" ? CheckCircle2 : data.tone === "danger" ? BellOff : Bell;
  const last = data.last_urgent_push;
  const healthy = data.tone === "ok" && (!data.issues || data.issues.length === 0);

  if (compactWhenOk && healthy) {
    return (
      <Link
        href="/notifications"
        data-testid="ops-push-health"
        className={cn(
          "inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1 text-[11px] font-medium",
          tone.ring,
          tone.label
        )}
        title="Push healthy — open Notifications"
      >
        <StatusIcon className={cn("h-3.5 w-3.5", tone.icon)} />
        Push ok
      </Link>
    );
  }

  return (
    <div
      className={cn(
        "flex flex-wrap items-center gap-x-4 gap-y-2 rounded-xl border px-3 py-2 text-xs",
        tone.ring
      )}
      data-testid="ops-push-health"
    >
      <span className={cn("flex items-center gap-1.5 font-semibold", tone.label)}>
        <StatusIcon className={cn("h-3.5 w-3.5", tone.icon)} />
        Push
        {data.fcm.credentials_configured && data.fcm.push_send
          ? " live"
          : data.fcm.push_enabled
            ? " log-only"
            : " off"}
      </span>
      <span className="flex items-center gap-1 text-primary/80">
        <Radio className="h-3.5 w-3.5 text-secondary" />
        Staff devices {data.devices.admin_users}
        <span className="text-muted">({data.devices.admin_active} tokens)</span>
      </span>
      <span className="flex items-center gap-1 text-primary/80">
        <Smartphone className="h-3.5 w-3.5 text-secondary" />
        Drivers {data.devices.driver_active}
      </span>
      <span className="text-primary/80">
        Critical 24h {data.critical_24h.delivered}/{data.critical_24h.total}
        {data.critical_24h.failed > 0 && (
          <span className="text-red-700"> · {data.critical_24h.failed} failed</span>
        )}
      </span>
      {last?.created_at && (
        <span className="text-muted">
          Last urgent {last.template_key} · {relativeTime(last.created_at)} · {last.status}
        </span>
      )}
      {data.issues?.[0] && (
        <span
          className={cn("max-w-md truncate font-medium", tone.label)}
          title={data.issues.join(" · ")}
        >
          {data.issues[0]}
        </span>
      )}
      <Link
        href="/notifications"
        className="ml-auto font-medium text-secondary underline-offset-2 hover:underline"
      >
        Notifications
      </Link>
    </div>
  );
}
