"use client";

import { useEffect, useMemo, useState } from "react";
import { Save } from "lucide-react";
import { Button, Field, Input, Select, Textarea } from "@/components/crm/primitives";
import {
  CONFIG_FIELD_SCHEMAS,
  SECTION_DESCRIPTIONS,
  getNestedValue,
  setNestedValue,
  type ConfigFieldDef,
} from "@/lib/settings-metadata";
import { BindingBadge, SettingsCard, SettingsPageHeader, Toggle } from "../ui/SettingsPrimitives";

type Props = {
  sectionId: string;
  data: unknown;
  onSave: (value: unknown, reason: string) => Promise<void>;
  saving?: boolean;
  effect?: string;
  envRuntime?: { quote_ttl_minutes?: number; booking_draft_ttl_minutes?: number | null };
};

const REASON_REQUIRED = new Set([
  "booking",
  "merchant",
  "driver",
  "customer",
  "finance",
  "coverage",
]);

export default function ConfigFormPanel({
  sectionId,
  data,
  onSave,
  saving,
  effect = "policy",
  envRuntime,
}: Props) {
  const schema = CONFIG_FIELD_SCHEMAS[sectionId];
  const title = sectionId.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  const description =
    SECTION_DESCRIPTIONS[sectionId] ?? "Runtime configuration stored in SystemConfig.";

  const initial = useMemo(() => data ?? {}, [data]);
  const [form, setForm] = useState<unknown>(initial);
  const [reason, setReason] = useState("");
  const [dirty, setDirty] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const hasPolicyFields = Boolean(schema?.some((f) => f.effect === "policy"));
  const hasWiredFields = Boolean(schema?.some((f) => f.effect === "wired"));

  useEffect(() => {
    setForm(initial);
    setDirty(false);
    setReason("");
    setError(null);
  }, [sectionId, initial]);

  function updateField(path: string, value: unknown) {
    const base =
      typeof form === "object" && form !== null && !Array.isArray(form)
        ? { ...(form as Record<string, unknown>) }
        : {};
    setForm(setNestedValue(base, path, value));
    setDirty(true);
  }

  async function handleSave() {
    if (REASON_REQUIRED.has(sectionId) && !reason.trim()) {
      setError(`Change reason required for ${sectionId}`);
      return;
    }
    try {
      setError(null);
      await onSave(form, reason.trim() || "Admin settings update");
      setDirty(false);
      setReason("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed");
    }
  }

  if (!schema?.length) {
    return <p className="text-sm text-muted">No structured fields for this section.</p>;
  }

  return (
    <div className="space-y-6">
      <SettingsPageHeader
        title={title}
        description={description}
        actions={
          <div className="flex items-center gap-2">
            <BindingBadge effect={effect} />
            <Button variant="primary" disabled={!dirty || saving} onClick={() => void handleSave()}>
              <Save className="h-4 w-4" /> {saving ? "Saving…" : "Save changes"}
            </Button>
          </div>
        }
      />

      {effect === "policy" && (
        <p className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
          Policy store — values are saved and audited but not all fields are enforced in runtime
          yet.
        </p>
      )}

      {effect === "wired" && hasPolicyFields && (
        <p className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
          Mixed section — wired fields change runtime immediately; fields marked Policy are stored
          only until a reader exists.
        </p>
      )}

      {effect !== "policy" && effect !== "wired" && hasWiredFields && hasPolicyFields && (
        <p className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
          Mixed section — check per-field badges for what is enforced.
        </p>
      )}

      {sectionId === "booking" && envRuntime && (
        <SettingsCard
          title="Quote & draft TTL (environment)"
          description="Runtime uses Doppler/env — not SystemConfig. Shown read-only."
        >
          <div className="grid gap-3 sm:grid-cols-2 text-sm">
            <div>
              <p className="text-xs text-muted">Quote TTL (minutes)</p>
              <p className="font-mono font-semibold">{envRuntime.quote_ttl_minutes ?? "—"}</p>
            </div>
            <div>
              <p className="text-xs text-muted">Draft TTL (minutes)</p>
              <p className="font-mono font-semibold">
                {envRuntime.booking_draft_ttl_minutes ?? "—"}
              </p>
            </div>
          </div>
          <BindingBadge effect="env" />
        </SettingsCard>
      )}

      <SettingsCard title="Configuration" description="Changes are audited with actor and reason">
        <div className="grid gap-4 sm:grid-cols-2">
          {schema.map((field) => (
            <ConfigField
              key={field.key}
              field={field}
              value={getNestedValue(
                typeof form === "object" && form !== null && !Array.isArray(form)
                  ? (form as Record<string, unknown>)
                  : {},
                field.key
              )}
              onChange={updateField}
            />
          ))}
        </div>
      </SettingsCard>

      <SettingsCard title="Change reason" description="Recorded in audit log">
        <Textarea
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          rows={2}
          placeholder={REASON_REQUIRED.has(sectionId) ? "Required for this section" : "Optional"}
        />
      </SettingsCard>
      {error && <p className="text-sm text-red-600">{error}</p>}
    </div>
  );
}

function ConfigField({
  field,
  value,
  onChange,
}: {
  field: ConfigFieldDef;
  value: unknown;
  onChange: (path: string, value: unknown) => void;
}) {
  const badge = field.effect ? (
    <div className="mb-2">
      <BindingBadge effect={field.effect} />
    </div>
  ) : null;

  if (field.type === "boolean") {
    return (
      <div className="sm:col-span-2">
        {badge}
        <Toggle
          label={field.label}
          hint={field.hint}
          checked={Boolean(value)}
          onChange={(v) => onChange(field.key, v)}
        />
      </div>
    );
  }

  if (field.type === "select" && field.options) {
    return (
      <div>
        {badge}
        <Field label={field.label} hint={field.hint}>
          <Select value={String(value ?? "")} onChange={(e) => onChange(field.key, e.target.value)}>
            {field.options.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </Select>
        </Field>
      </div>
    );
  }

  if (field.moneyCents) {
    const dollars = typeof value === "number" ? value / 100 : "";
    return (
      <div>
        {badge}
        <Field label={field.label} hint={field.hint}>
          <Input
            type="number"
            min={field.min}
            max={field.max}
            step={field.step ?? 0.01}
            value={dollars === "" ? "" : String(dollars)}
            onChange={(e) => {
              const n = Number(e.target.value);
              onChange(
                field.key,
                e.target.value === "" || !Number.isFinite(n) ? null : Math.round(n * 100)
              );
            }}
          />
        </Field>
      </div>
    );
  }

  return (
    <div>
      {badge}
      <Field label={field.label} hint={field.hint}>
        <Input
          type={field.type === "number" ? "number" : field.type === "email" ? "email" : "text"}
          min={field.min}
          max={field.max}
          step={field.step}
          value={value == null ? "" : String(value)}
          onChange={(e) => {
            if (field.type === "number") {
              const n = Number(e.target.value);
              onChange(field.key, e.target.value === "" || !Number.isFinite(n) ? null : n);
            } else {
              onChange(field.key, e.target.value);
            }
          }}
        />
      </Field>
    </div>
  );
}
