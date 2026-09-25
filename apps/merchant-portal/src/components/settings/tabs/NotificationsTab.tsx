"use client";

import { useEffect, useState } from "react";
import Button from "@/components/ui/Button";
import { notificationsApi } from "@/lib/notifications";
import { settingsApi, type NotificationPrefs, type QuietHours } from "@/lib/settings";

function hourLabel(hour: number): string {
  const period = hour >= 12 ? "pm" : "am";
  const hour12 = hour % 12 === 0 ? 12 : hour % 12;
  return `${hour12}:00 ${period}`;
}

const DEFAULT_QUIET: QuietHours = {
  quiet_hours_enabled: false,
  quiet_start_hour: 22,
  quiet_end_hour: 7,
  timezone: "America/Toronto",
};

export function NotificationsTab({
  prefs,
  quietHours,
  onRefresh,
  getToken,
  orgId,
}: {
  prefs: NotificationPrefs;
  quietHours?: QuietHours;
  onRefresh: () => Promise<void>;
  getToken: () => Promise<string>;
  orgId?: string;
}) {
  const [quiet, setQuiet] = useState<QuietHours>(quietHours ?? DEFAULT_QUIET);
  const [quietBusy, setQuietBusy] = useState(false);
  const [quietMessage, setQuietMessage] = useState<string | null>(null);

  useEffect(() => {
    if (quietHours) setQuiet(quietHours);
  }, [quietHours]);

  const toggle = async (key: keyof NotificationPrefs, value: boolean) => {
    const token = await getToken();
    await settingsApi.updateNotifications(token, { [key]: value }, orgId);
    await onRefresh();
  };

  const toggleChannel = async (channel: "email" | "in_app", value: boolean) => {
    const token = await getToken();
    await settingsApi.updateNotifications(
      token,
      { channels: { ...prefs.channels, [channel]: value } },
      orgId
    );
    await onRefresh();
  };

  const saveQuiet = async (next: QuietHours) => {
    setQuietBusy(true);
    setQuietMessage(null);
    try {
      const token = await getToken();
      const saved = await notificationsApi.updateQuietHours(
        token,
        { ...next, timezone: "America/Toronto" },
        orgId
      );
      setQuiet(saved);
      await onRefresh();
      setQuietMessage("Quiet hours saved.");
    } catch (e) {
      setQuietMessage(e instanceof Error ? e.message : "Could not save quiet hours");
    } finally {
      setQuietBusy(false);
    }
  };

  const items: { key: keyof NotificationPrefs; label: string }[] = [
    { key: "order_booked", label: "Order booked" },
    { key: "order_delivered", label: "Order delivered" },
    { key: "order_failed", label: "Failed delivery" },
    { key: "invoice_generated", label: "Invoice generated" },
    { key: "payment_received", label: "Payment received" },
    { key: "claim_updates", label: "Claim updates" },
    { key: "support_replies", label: "Support replies" },
    { key: "weekly_summary", label: "Weekly summary" },
  ];

  const channels = prefs.channels ?? { email: true, in_app: true };

  return (
    <div className="space-y-5">
      <section className="rounded-2xl border border-primary/10 bg-white p-6">
        <h2 className="font-semibold text-primary">Notification preferences</h2>
        <p className="mt-1 text-xs text-muted">
          Changes apply to this company (email and in-app). SMS stays off until enabled.
        </p>
        <div className="mt-4 flex flex-wrap gap-6 border-b border-primary/8 pb-4">
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={Boolean(channels.email)}
              onChange={(e) => void toggleChannel("email", e.target.checked)}
            />
            Email
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={Boolean(channels.in_app)}
              onChange={(e) => void toggleChannel("in_app", e.target.checked)}
            />
            In-app
          </label>
        </div>
        <ul className="mt-4 space-y-3">
          {items.map((item) => (
            <li key={item.key} className="flex items-center justify-between text-sm">
              <span>{item.label}</span>
              <input
                type="checkbox"
                checked={Boolean(prefs[item.key])}
                onChange={(e) => void toggle(item.key, e.target.checked)}
              />
            </li>
          ))}
        </ul>
      </section>
      <section className="rounded-2xl border border-primary/10 bg-white p-6">
        <h2 className="font-semibold text-primary">Quiet hours</h2>
        <p className="mt-1 text-sm text-muted">
          Pause push alerts overnight. Email and in-app still arrive. Urgent alerts still go
          through. Times are Eastern Time (Toronto).
        </p>
        <label className="mt-4 flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={quiet.quiet_hours_enabled}
            disabled={quietBusy}
            onChange={(e) => void saveQuiet({ ...quiet, quiet_hours_enabled: e.target.checked })}
          />
          Pause push during quiet hours
        </label>
        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          <label className="text-sm">
            <span className="text-muted">Start</span>
            <select
              className="mt-1 w-full rounded-lg border border-primary/15 px-3 py-2"
              value={quiet.quiet_start_hour}
              disabled={quietBusy}
              onChange={(e) =>
                void saveQuiet({ ...quiet, quiet_start_hour: Number(e.target.value) })
              }
            >
              {Array.from({ length: 24 }, (_, hour) => (
                <option key={`start-${hour}`} value={hour}>
                  {hourLabel(hour)}
                </option>
              ))}
            </select>
          </label>
          <label className="text-sm">
            <span className="text-muted">End</span>
            <select
              className="mt-1 w-full rounded-lg border border-primary/15 px-3 py-2"
              value={quiet.quiet_end_hour}
              disabled={quietBusy}
              onChange={(e) => void saveQuiet({ ...quiet, quiet_end_hour: Number(e.target.value) })}
            >
              {Array.from({ length: 24 }, (_, hour) => (
                <option key={`end-${hour}`} value={hour}>
                  {hourLabel(hour)}
                </option>
              ))}
            </select>
          </label>
        </div>
        {quietMessage ? <p className="mt-3 text-sm text-muted">{quietMessage}</p> : null}
      </section>
    </div>
  );
}
