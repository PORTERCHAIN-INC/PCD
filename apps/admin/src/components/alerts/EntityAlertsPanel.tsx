"use client";

import Link from "next/link";
import { Bell, Smartphone } from "lucide-react";
import { useApiData } from "@/hooks/useApiData";
import { notificationsApi } from "@/lib/notifications";
import { Badge, EmptyState, SectionCard, Spinner } from "@/components/crm/primitives";
import { relativeTime, titleCase } from "@/lib/crmFormat";

const STATUS_TONE: Record<string, string> = {
  sent: "green",
  delivered: "green",
  queued: "amber",
  failed: "red",
  dead_letter: "red",
  suppressed: "slate",
};

type RecipientType = "merchant" | "driver" | "customer";

export function EntityAlertsPanel({
  recipientType,
  recipientId,
  showDevices = false,
  careHref,
}: {
  recipientType: RecipientType;
  recipientId: string;
  showDevices?: boolean;
  /** Optional deep-link for care counts (support / incidents / operations). */
  careHref?: string;
}) {
  const { data, error, loading } = useApiData(
    (t) =>
      notificationsApi.entityAlerts(t, {
        recipient_type: recipientType,
        recipient_id: recipientId,
      }),
    [recipientType, recipientId],
    { key: `entity-alerts-${recipientType}-${recipientId}` }
  );

  if (loading && !data) {
    return (
      <SectionCard title="Alerts & preferences">
        <Spinner label="Loading alerts…" />
      </SectionCard>
    );
  }

  if (error || !data) {
    return (
      <SectionCard title="Alerts & preferences">
        <EmptyState title="Could not load alerts" hint={error || "notifications_read required"} />
      </SectionCard>
    );
  }

  const quiet = data.settings;
  const careBits = [
    data.care.open_exceptions > 0 ? `${data.care.open_exceptions} exceptions` : null,
    data.care.open_support_tickets > 0 ? `${data.care.open_support_tickets} support` : null,
    data.care.open_claims > 0 ? `${data.care.open_claims} claims` : null,
  ].filter(Boolean);

  return (
    <SectionCard
      title="Alerts & preferences"
      action={
        <div className="flex flex-wrap gap-2">
          <Link
            href={data.links.notifications_history}
            className="text-xs font-medium text-secondary hover:underline"
          >
            Open notifications
          </Link>
          {showDevices && (
            <Link
              href={data.links.notifications_devices}
              className="text-xs font-medium text-secondary hover:underline"
            >
              Devices
            </Link>
          )}
        </div>
      }
    >
      <div className="space-y-5 p-5">
        <div className="flex flex-wrap gap-2">
          {quiet.quiet_hours_enabled ? (
            <Badge tone="amber">
              Quiet hours {quiet.quiet_start_hour}:00–{quiet.quiet_end_hour}:00 ({quiet.timezone})
            </Badge>
          ) : (
            <Badge tone="slate">Quiet hours off</Badge>
          )}
          {data.muted_categories.length > 0 ? (
            <Badge tone="amber">Muted: {data.muted_categories.join(", ")}</Badge>
          ) : (
            <Badge tone="green">No fully muted categories</Badge>
          )}
          {careBits.length > 0 &&
            (careHref ? (
              <Link href={careHref}>
                <Badge tone="red">{careBits.join(" · ")}</Badge>
              </Link>
            ) : (
              <Badge tone="red">{careBits.join(" · ")}</Badge>
            ))}
          {showDevices && (
            <Badge tone={data.devices.length ? "sky" : "slate"}>
              <Smartphone className="mr-1 inline h-3 w-3" />
              {data.devices.length} device{data.devices.length === 1 ? "" : "s"}
            </Badge>
          )}
        </div>

        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted">
            Recent notifications
          </p>
          {data.recent.length === 0 ? (
            <p className="flex items-center gap-2 text-sm text-muted">
              <Bell className="h-4 w-4" /> No notification records yet for this node.
            </p>
          ) : (
            <div className="divide-y divide-primary/5 rounded-xl border border-primary/10">
              {data.recent.slice(0, 8).map((r) => (
                <div key={r.id} className="flex items-start justify-between gap-3 px-3 py-2.5">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-primary">
                      {r.title || r.template_key}
                    </p>
                    <p className="truncate text-xs text-muted">
                      {r.channel} · {r.template_key}
                      {r.body ? ` — ${r.body.slice(0, 80)}` : ""}
                    </p>
                  </div>
                  <div className="shrink-0 text-right">
                    <Badge tone={STATUS_TONE[r.status] ?? "slate"}>{titleCase(r.status)}</Badge>
                    <p className="mt-1 text-[11px] text-muted">{relativeTime(r.created_at)}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {showDevices && data.devices.length > 0 && (
          <div>
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted">
              Push devices
            </p>
            <ul className="space-y-1 text-sm text-primary">
              {data.devices.map((d) => (
                <li key={d.id} className="flex justify-between gap-2 text-xs">
                  <span>
                    {d.device_name || d.platform}
                    {d.app_version ? ` · ${d.app_version}` : ""}
                  </span>
                  <span className="text-muted">
                    {d.last_seen_at ? relativeTime(d.last_seen_at) : "—"}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </SectionCard>
  );
}
