"use client";

import { useEffect, useState } from "react";
import Button from "@/components/ui/Button";
import {
  CX_EVENT_LABELS,
  CX_PRESET_LABELS,
  cxCustomerFacingSummary,
  cxValidationError,
  type CustomerExperienceSettings,
  type CxEvent,
} from "@/lib/customerExperience";
import { settingsApi } from "@/lib/settings";
import { Field } from "./Field";

function Toggle({
  label,
  checked,
  onChange,
  disabled,
  hint,
}: {
  label: string;
  checked: boolean;
  onChange: (v: boolean) => void;
  disabled?: boolean;
  hint?: string;
}) {
  return (
    <label className="flex items-start gap-3 text-sm text-primary">
      <input
        type="checkbox"
        className="mt-1"
        checked={checked}
        disabled={disabled}
        onChange={(e) => onChange(e.target.checked)}
      />
      <span>
        {label}
        {hint ? <span className="block text-xs text-muted">{hint}</span> : null}
      </span>
    </label>
  );
}

function NumberField({
  label,
  value,
  onChange,
  min,
  max,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
  min: number;
  max: number;
}) {
  return (
    <label className="block text-sm font-medium text-primary">
      {label}
      <input
        type="number"
        min={min}
        max={max}
        className="mt-1 w-28 rounded-xl border border-primary/15 px-3 py-2 text-sm"
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
      />
    </label>
  );
}

export function CustomerExperienceTab({
  getToken,
  orgId,
}: {
  getToken: () => Promise<string>;
  orgId?: string;
}) {
  const [form, setForm] = useState<CustomerExperienceSettings | null>(null);
  const [presets, setPresets] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    let cancelled = false;
    getToken()
      .then((token) => settingsApi.customerExperience(token, orgId))
      .then((res) => {
        if (cancelled) return;
        setForm(res.settings);
        setPresets(res.presets);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Could not load settings."));
    return () => {
      cancelled = true;
    };
  }, [getToken, orgId]);

  const save = async (preset?: string) => {
    if (!form) return;
    setError(null);
    setSaved(false);
    const problem = cxValidationError(form);
    if (problem) {
      setError(problem);
      return;
    }
    try {
      const token = await getToken();
      const res = await settingsApi.updateCustomerExperience(
        token,
        preset ? { ...form, preset } : form,
        orgId
      );
      setForm(res.settings);
      setSaved(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save settings.");
    }
  };

  if (!form) {
    return (
      <section className="rounded-2xl border border-primary/10 bg-white p-6 text-sm text-muted">
        {error ?? "Loading…"}
      </section>
    );
  }

  const set = <K extends keyof CustomerExperienceSettings>(
    key: K,
    patch: Partial<CustomerExperienceSettings[K]>
  ) => setForm({ ...form, [key]: { ...form[key], ...patch } });
  const summary = cxCustomerFacingSummary(form);

  return (
    <section className="space-y-6 rounded-2xl border border-primary/10 bg-white p-6">
      <div>
        <h2 className="font-semibold text-primary">Customer experience</h2>
        <p className="text-sm text-muted">
          What your recipients see and receive. Everything starts off; nothing changes for
          recipients until you turn it on. Messages are delivery updates only (no marketing).
        </p>
        <p className="mt-2 text-sm text-primary">
          {summary.length
            ? `Recipients get: ${summary.join("; ")}.`
            : "Recipients get the standard PorterChain track page."}
        </p>
      </div>

      <div className="space-y-3">
        <h3 className="text-sm font-semibold text-primary">Tracking page</h3>
        <Toggle
          label="Branded tracking page (logo, colours, timeline, delivery window)"
          checked={form.tracking.branded_page}
          onChange={(v) => set("tracking", { branded_page: v })}
        />
        <Toggle
          label="Show driver first name"
          checked={form.tracking.show_driver_first_name}
          onChange={(v) => set("tracking", { show_driver_first_name: v })}
        />
        <Toggle
          label="Show how many stops are before theirs"
          checked={form.tracking.show_stops_away}
          onChange={(v) => set("tracking", { show_stops_away: v })}
        />
        <Toggle
          label="Show proof-of-delivery photos (only via the recipient's secure link)"
          checked={form.tracking.show_pod_photo}
          onChange={(v) => set("tracking", { show_pod_photo: v })}
        />
        <Field
          label="Support email shown to recipients"
          value={form.tracking.support_email ?? ""}
          onChange={(v) => set("tracking", { support_email: v || null })}
        />
        <Field
          label="Support phone"
          value={form.tracking.support_phone ?? ""}
          onChange={(v) => set("tracking", { support_phone: v || null })}
        />
        <Field
          label="Help page (https://)"
          value={form.tracking.help_url ?? ""}
          onChange={(v) => set("tracking", { help_url: v || null })}
        />
      </div>

      <div className="space-y-3">
        <h3 className="text-sm font-semibold text-primary">Delivery updates</h3>
        <Toggle
          label="Send delivery updates to recipients"
          checked={form.notifications.enabled}
          onChange={(v) => set("notifications", { enabled: v })}
        />
        <div className="flex flex-wrap gap-6">
          <Toggle
            label="Email"
            checked={form.notifications.channels.email}
            onChange={(v) =>
              set("notifications", { channels: { ...form.notifications.channels, email: v } })
            }
          />
          <Toggle
            label="SMS"
            checked={form.notifications.channels.sms}
            onChange={(v) =>
              set("notifications", { channels: { ...form.notifications.channels, sms: v } })
            }
          />
          <Toggle
            label="WhatsApp"
            checked={false}
            disabled
            onChange={() => undefined}
            hint="Not available yet"
          />
        </div>
        {(Object.keys(CX_EVENT_LABELS) as CxEvent[]).map((ev) => (
          <Toggle
            key={ev}
            label={CX_EVENT_LABELS[ev]}
            checked={form.notifications.events[ev]}
            onChange={(v) =>
              set("notifications", { events: { ...form.notifications.events, [ev]: v } })
            }
          />
        ))}
        <div className="flex flex-wrap gap-6">
          <NumberField
            label="'Minutes away' alert"
            min={5}
            max={120}
            value={form.notifications.eta_minutes}
            onChange={(v) => set("notifications", { eta_minutes: v })}
          />
          <NumberField
            label="'You're next' when stops before ≤"
            min={0}
            max={10}
            value={form.notifications.next_stop_threshold}
            onChange={(v) => set("notifications", { next_stop_threshold: v })}
          />
        </div>
        <Toggle
          label="Quiet hours for SMS (email still sends)"
          checked={form.notifications.quiet_hours.enabled}
          onChange={(v) =>
            set("notifications", { quiet_hours: { ...form.notifications.quiet_hours, enabled: v } })
          }
        />
        <div className="flex gap-4">
          <Field
            label="Quiet from"
            value={form.notifications.quiet_hours.start}
            onChange={(v) =>
              set("notifications", { quiet_hours: { ...form.notifications.quiet_hours, start: v } })
            }
          />
          <Field
            label="Quiet until"
            value={form.notifications.quiet_hours.end}
            onChange={(v) =>
              set("notifications", { quiet_hours: { ...form.notifications.quiet_hours, end: v } })
            }
          />
        </div>
      </div>

      <div className="space-y-3">
        <h3 className="text-sm font-semibold text-primary">Recipient self-service</h3>
        <Toggle
          label="Let recipients manage their delivery via a secure link"
          checked={form.self_service.enabled}
          onChange={(v) => set("self_service", { enabled: v })}
        />
        <Toggle
          label="Allow choosing / changing the delivery window"
          checked={form.self_service.allow_reschedule}
          onChange={(v) => set("self_service", { allow_reschedule: v })}
        />
        <Toggle
          label="Allow gate code, buzzer and safe-place instructions"
          checked={form.self_service.allow_instructions}
          onChange={(v) => set("self_service", { allow_instructions: v })}
        />
        <div className="flex flex-wrap gap-6">
          <NumberField
            label="Link valid (hours)"
            min={1}
            max={336}
            value={form.self_service.link_ttl_hours}
            onChange={(v) => set("self_service", { link_ttl_hours: v })}
          />
          <NumberField
            label="Days to choose from"
            min={1}
            max={21}
            value={form.self_service.schedule_days}
            onChange={(v) => set("self_service", { schedule_days: v })}
          />
        </div>
      </div>

      <div className="space-y-3">
        <h3 className="text-sm font-semibold text-primary">Delivery rules</h3>
        <Toggle
          label="Safe place allowed when no one is home"
          checked={form.delivery_rules.safe_place_allowed}
          onChange={(v) => set("delivery_rules", { safe_place_allowed: v })}
        />
        <Toggle
          label="Photo ID required"
          checked={form.delivery_rules.id_required}
          onChange={(v) => set("delivery_rules", { id_required: v })}
        />
        <Toggle
          label="Signature required"
          checked={form.delivery_rules.signature_required}
          onChange={(v) => set("delivery_rules", { signature_required: v })}
        />
        <Toggle
          label="Bulky items: recipient must pick a time before we dispatch"
          hint={`Applies to package types: ${form.delivery_rules.bulky_package_types.join(", ")}. Needs self-service on.`}
          checked={form.delivery_rules.require_schedule_for_bulky}
          onChange={(v) => set("delivery_rules", { require_schedule_for_bulky: v })}
        />
      </div>

      <div className="space-y-3">
        <h3 className="text-sm font-semibold text-primary">Failed deliveries</h3>
        <Toggle
          label="Apply a re-attempt policy"
          hint="Each re-attempt or return is quoted by your normal rates. Contract schedules do not include failed-delivery fees yet."
          checked={form.reattempt.enabled}
          onChange={(v) => set("reattempt", { enabled: v })}
        />
        <div className="flex flex-wrap gap-6">
          <NumberField
            label="Max delivery attempts"
            min={1}
            max={5}
            value={form.reattempt.max_attempts}
            onChange={(v) => set("reattempt", { max_attempts: v })}
          />
          <NumberField
            label="Return to sender after"
            min={1}
            max={5}
            value={form.reattempt.return_to_sender_after}
            onChange={(v) => set("reattempt", { return_to_sender_after: v })}
          />
        </div>
      </div>

      {presets.length ? (
        <div className="space-y-2">
          <h3 className="text-sm font-semibold text-primary">Presets</h3>
          {presets.map((p) => (
            <Button key={p} size="sm" variant="secondary" onClick={() => void save(p)}>
              {CX_PRESET_LABELS[p] ?? p}
            </Button>
          ))}
        </div>
      ) : null}

      {error ? <p className="text-sm text-red-600">{error}</p> : null}
      {saved ? <p className="text-sm text-green-700">Saved.</p> : null}
      <Button size="sm" onClick={() => void save()}>
        Save customer experience
      </Button>
    </section>
  );
}
