"use client";

import { useEffect, useMemo, useState } from "react";
import { Save } from "lucide-react";
import { Button, Field, Input, Select, Textarea } from "@/components/crm/primitives";
import {
  CONFIG_FIELD_SCHEMAS,
  FEATURE_FLAG_LABELS,
  SECTION_DESCRIPTIONS,
  getNestedValue,
  setNestedValue,
  type ConfigFieldDef,
} from "@/lib/settings-metadata";
import { SettingsCard, SettingsPageHeader, Toggle } from "../ui/SettingsPrimitives";

type Props = {
  sectionId: string;
  data: unknown;
  onSave: (value: unknown, reason: string) => Promise<void>;
  saving?: boolean;
};

export default function ConfigFormPanel({ sectionId, data, onSave, saving }: Props) {
  const schema = CONFIG_FIELD_SCHEMAS[sectionId];
  const title = sectionId.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  const description =
    SECTION_DESCRIPTIONS[sectionId] ?? "Runtime configuration stored in SystemConfig.";

  const initial = useMemo(() => data ?? {}, [data]);
  const [form, setForm] = useState<unknown>(initial);
  const [reason, setReason] = useState("");
  const [dirty, setDirty] = useState(false);

  useEffect(() => {
    setForm(initial);
    setDirty(false);
    setReason("");
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
    await onSave(form, reason || "Admin settings update");
    setDirty(false);
    setReason("");
  }

  if (sectionId === "feature_flags") {
    const flags = (typeof form === "object" && form !== null ? form : {}) as Record<
      string,
      boolean
    >;
    return (
      <div className="space-y-6">
        <SettingsPageHeader
          title="Feature flags"
          description={description}
          actions={
            <Button variant="primary" disabled={!dirty || saving} onClick={() => void handleSave()}>
              <Save className="h-4 w-4" /> {saving ? "Saving…" : "Save changes"}
            </Button>
          }
        />
        <SettingsCard
          title="Rollout toggles"
          description="Gradual feature enablement — no redeploy required"
        >
          <div className="space-y-2">
            {Object.entries(flags).map(([key, val]) => (
              <Toggle
                key={key}
                label={FEATURE_FLAG_LABELS[key] ?? key}
                hint={`Flag: ${key}`}
                checked={Boolean(val)}
                onChange={(v) => updateField(key, v)}
              />
            ))}
          </div>
        </SettingsCard>
        <ReasonField reason={reason} onReason={setReason} />
      </div>
    );
  }

  if (
    sectionId === "service_areas" ||
    sectionId === "delivery_zones" ||
    sectionId === "notifications"
  ) {
    return (
      <JsonConfigPanel
        title={title}
        description={description}
        data={form}
        onChange={(v) => {
          setForm(v);
          setDirty(true);
        }}
        onSave={handleSave}
        saving={saving}
        dirty={dirty}
        reason={reason}
        onReason={setReason}
      />
    );
  }

  if (!schema?.length) {
    return (
      <JsonConfigPanel
        title={title}
        description={description}
        data={form}
        onChange={(v) => {
          setForm(v);
          setDirty(true);
        }}
        onSave={handleSave}
        saving={saving}
        dirty={dirty}
        reason={reason}
        onReason={setReason}
      />
    );
  }

  return (
    <div className="space-y-6">
      <SettingsPageHeader
        title={title}
        description={description}
        actions={
          <Button variant="primary" disabled={!dirty || saving} onClick={() => void handleSave()}>
            <Save className="h-4 w-4" /> {saving ? "Saving…" : "Save changes"}
          </Button>
        }
      />
      <SettingsCard
        title="Configuration"
        description="Changes are audited with actor and optional reason"
      >
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
      <ReasonField reason={reason} onReason={setReason} />
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
  if (field.type === "boolean") {
    return (
      <div className="sm:col-span-2">
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
      <Field label={field.label} hint={field.hint}>
        <Select value={String(value ?? "")} onChange={(e) => onChange(field.key, e.target.value)}>
          {field.options.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </Select>
      </Field>
    );
  }

  if (field.type === "json") {
    return (
      <Field label={field.label} hint={field.hint} className="sm:col-span-2">
        <Textarea
          rows={4}
          className="font-mono text-xs"
          value={typeof value === "string" ? value : JSON.stringify(value ?? [], null, 2)}
          onChange={(e) => {
            try {
              onChange(field.key, JSON.parse(e.target.value));
            } catch {
              onChange(field.key, e.target.value);
            }
          }}
        />
      </Field>
    );
  }

  if (field.type === "color") {
    return (
      <Field label={field.label} hint={field.hint}>
        <div className="flex gap-2">
          <input
            type="color"
            value={String(value ?? "#2563eb")}
            onChange={(e) => onChange(field.key, e.target.value)}
            className="h-10 w-12 cursor-pointer rounded-lg border border-primary/15"
          />
          <Input
            value={String(value ?? "")}
            onChange={(e) => onChange(field.key, e.target.value)}
          />
        </div>
      </Field>
    );
  }

  return (
    <Field label={field.label} hint={field.hint}>
      <Input
        type={field.type === "number" ? "number" : field.type === "email" ? "email" : "text"}
        min={field.min}
        max={field.max}
        step={field.step}
        value={value == null ? "" : String(value)}
        onChange={(e) =>
          onChange(field.key, field.type === "number" ? Number(e.target.value) : e.target.value)
        }
      />
    </Field>
  );
}

function ReasonField({ reason, onReason }: { reason: string; onReason: (v: string) => void }) {
  return (
    <SettingsCard
      title="Change reason"
      description="Optional — recorded in audit log for compliance"
    >
      <Input
        placeholder="e.g. Updated quote TTL per ops review"
        value={reason}
        onChange={(e) => onReason(e.target.value)}
      />
    </SettingsCard>
  );
}

function JsonConfigPanel({
  title,
  description,
  data,
  onChange,
  onSave,
  saving,
  dirty,
  reason,
  onReason,
}: {
  title: string;
  description: string;
  data: unknown;
  onChange: (v: unknown) => void;
  onSave: () => Promise<void>;
  saving?: boolean;
  dirty: boolean;
  reason: string;
  onReason: (v: string) => void;
}) {
  const [raw, setRaw] = useState(() => JSON.stringify(data, null, 2));
  const [parseError, setParseError] = useState<string | null>(null);

  useEffect(() => {
    setRaw(JSON.stringify(data, null, 2));
    setParseError(null);
  }, [data]);

  return (
    <div className="space-y-6">
      <SettingsPageHeader
        title={title}
        description={description}
        actions={
          <Button
            variant="primary"
            disabled={!dirty || saving || !!parseError}
            onClick={() => void onSave()}
          >
            <Save className="h-4 w-4" /> {saving ? "Saving…" : "Save changes"}
          </Button>
        }
      />
      <SettingsCard
        title="Structured data"
        description="Arrays and complex objects — validated before save"
      >
        <Textarea
          rows={16}
          className="font-mono text-xs"
          value={raw}
          onChange={(e) => {
            setRaw(e.target.value);
            try {
              const parsed = JSON.parse(e.target.value) as unknown;
              onChange(parsed);
              setParseError(null);
            } catch {
              setParseError("Invalid JSON");
            }
          }}
        />
        {parseError && <p className="mt-2 text-xs text-red-600">{parseError}</p>}
      </SettingsCard>
      <ReasonField reason={reason} onReason={onReason} />
    </div>
  );
}
