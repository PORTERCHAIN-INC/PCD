"use client";

import { useEffect, useState } from "react";
import { Button, Field, Input, Textarea } from "@/components/crm/primitives";
import { useOptionalAdminProfile } from "@/components/nav/AdminProfileContext";
import {
  DELIVERY_PROMISE_PLACEHOLDERS,
  parseHolidays,
  parsePrefixes,
  SERVICE_KINDS,
  toggleWeekday,
  waveProblems,
  WEEKDAYS,
  type PromiseTier,
  type PromiseWave,
} from "@/lib/delivery-promise";
import { asObject, getPath, setPath, wholeNumber, type JsonObject } from "@/lib/price-book";
import { SettingsCard } from "../ui/SettingsPrimitives";

type Props = {
  data: unknown;
  saving?: boolean;
  onSave: (value: JsonObject, reason: string) => Promise<void>;
};

function Example({ path }: { path: string }) {
  if (!DELIVERY_PROMISE_PLACEHOLDERS.includes(path)) return null;
  return (
    <span className="ml-1 rounded bg-amber-100 px-1.5 py-0.5 text-[10px] font-semibold uppercase text-amber-900">
      Example
    </span>
  );
}

/**
 * Checkout delivery promise shown on PorterChain's Shopify rate (service name,
 * description and min/max delivery dates). Off by default: checkout keeps the
 * fixed same-day window until a super admin turns this on. Prices never change.
 */
export default function DeliveryPromisePanel({ data, saving, onSave }: Props) {
  const profile = useOptionalAdminProfile();
  const canEdit = (profile?.role || "").toLowerCase() === "super_admin";
  const [cfg, setCfg] = useState<JsonObject>(() => asObject(data));
  const [holidayText, setHolidayText] = useState("");
  const [dirty, setDirty] = useState(false);
  const [reason, setReason] = useState("");
  const [toast, setToast] = useState<string | null>(null);

  useEffect(() => {
    const next = asObject(data);
    setCfg(next);
    setHolidayText(((next.holidays as string[]) ?? []).join("\n"));
  }, [data]);

  function edit(path: string, value: unknown) {
    setCfg((c) => setPath(c, path, value));
    setDirty(true);
  }

  const waves = (Array.isArray(cfg.waves) ? cfg.waves : []) as PromiseWave[];
  const tiers = (Array.isArray(cfg.fsa_tiers) ? cfg.fsa_tiers : []) as PromiseTier[];
  const weekdays = (
    Array.isArray(cfg.operating_weekdays) ? cfg.operating_weekdays : []
  ) as number[];
  const holidays = parseHolidays(holidayText);
  const problems = [
    ...waveProblems(waves),
    ...(holidays.invalid.length ? [`Not a date (YYYY-MM-DD): ${holidays.invalid.join(", ")}`] : []),
    ...(weekdays.length ? [] : ["Pick at least one delivery day."]),
  ];

  async function save() {
    if (!reason.trim()) {
      setToast("Change reason required");
      return;
    }
    if (problems.length) {
      setToast(problems[0] ?? "Fix the highlighted fields");
      return;
    }
    try {
      await onSave({ ...cfg, holidays: holidays.dates }, reason.trim());
      setDirty(false);
      setReason("");
      setToast("Saved — new checkout rates use this promise");
    } catch (e) {
      setToast(e instanceof Error ? e.message : "Save failed");
    }
  }

  const time = (path: string) => (
    <Input
      disabled={!canEdit}
      placeholder="HH:MM"
      value={String(getPath(cfg, path) ?? "")}
      onChange={(e) => edit(path, e.target.value)}
    />
  );

  return (
    <div className="space-y-6">
      <p className="rounded-xl border border-primary/10 bg-primary/5 px-3 py-2 text-sm">
        Super admin only. {canEdit ? "" : "You can view these values; saving needs a super admin. "}
        Off = checkout keeps the fixed same-day window. Fields marked <Example path="waves" /> are
        placeholders waiting for an ops decision. Prices are not affected.
      </p>
      {toast && <p className="text-sm text-secondary">{toast}</p>}

      <SettingsCard
        title="Checkout delivery promise"
        description={`Times are local to ${String(cfg.timezone ?? "America/Toronto")}. An order placed before a wave's cut-off makes that wave today; later orders get the first wave of the next delivery day.`}
      >
        <div className="space-y-4">
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              disabled={!canEdit}
              checked={Boolean(cfg.enabled)}
              onChange={(e) => edit("enabled", e.target.checked)}
            />
            Use this promise on Shopify checkout rates
          </label>

          <table className="w-full text-left text-sm">
            <thead>
              <tr className="text-xs uppercase text-muted">
                <th className="py-1">
                  Wave
                  <Example path="waves" />
                </th>
                <th className="py-1">Order by</th>
                <th className="py-1">Delivered from</th>
                <th className="py-1">Until</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {waves.map((w, i) => (
                <tr key={i} className="border-t border-primary/5">
                  <td className="py-1 pr-2">
                    <Input
                      disabled={!canEdit}
                      value={w.code}
                      onChange={(e) => edit(`waves.${i}.code`, e.target.value)}
                    />
                  </td>
                  <td className="py-1 pr-2">{time(`waves.${i}.cutoff`)}</td>
                  <td className="py-1 pr-2">{time(`waves.${i}.start`)}</td>
                  <td className="py-1 pr-2">{time(`waves.${i}.end`)}</td>
                  <td className="py-1">
                    {canEdit && waves.length > 1 ? (
                      <Button
                        variant="outline"
                        onClick={() =>
                          edit(
                            "waves",
                            waves.filter((_, j) => j !== i)
                          )
                        }
                      >
                        Remove
                      </Button>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {canEdit && waves.length < 8 ? (
            <Button
              variant="outline"
              onClick={() =>
                edit("waves", [
                  ...waves,
                  { code: `w${waves.length + 1}`, cutoff: "15:00", start: "18:00", end: "22:00" },
                ])
              }
            >
              Add wave
            </Button>
          ) : null}

          <div>
            <p className="text-sm font-medium">
              Delivery days
              <Example path="operating_weekdays" />
            </p>
            <div className="mt-1 flex flex-wrap gap-3">
              {WEEKDAYS.map((label, day) => (
                <label key={label} className="flex items-center gap-1 text-sm">
                  <input
                    type="checkbox"
                    disabled={!canEdit}
                    checked={weekdays.includes(day)}
                    onChange={() => edit("operating_weekdays", toggleWeekday(weekdays, day))}
                  />
                  {label}
                </label>
              ))}
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="Holidays (no deliveries), one YYYY-MM-DD per line · EXAMPLE">
              <Textarea
                rows={4}
                disabled={!canEdit}
                value={holidayText}
                onChange={(e) => {
                  setHolidayText(e.target.value);
                  setDirty(true);
                }}
              />
            </Field>
            <Field label="Never promise more than (days ahead)">
              <Input
                type="number"
                min="1"
                max="60"
                disabled={!canEdit}
                value={String(cfg.max_days_ahead ?? 14)}
                onChange={(e) => edit("max_days_ahead", wholeNumber(e.target.value, 14))}
              />
            </Field>
          </div>
        </div>
      </SettingsCard>

      <SettingsCard
        title="FSA tiers"
        description="Destination FSA prefixes (e.g. L9, K0A) that cannot get same-day and/or add delivery days. Most specific prefix wins."
      >
        <div className="space-y-2">
          {tiers.length === 0 ? (
            <p className="text-sm text-muted">
              No tiers: every in-area FSA gets the same promise.
              <Example path="fsa_tiers" />
            </p>
          ) : null}
          {tiers.map((t, i) => (
            <div key={i} className="grid items-end gap-2 sm:grid-cols-5">
              <Field label="Name">
                <Input
                  disabled={!canEdit}
                  value={t.name}
                  onChange={(e) => edit(`fsa_tiers.${i}.name`, e.target.value)}
                />
              </Field>
              <Field label="FSA prefixes">
                <Input
                  disabled={!canEdit}
                  value={(t.prefixes ?? []).join(", ")}
                  onChange={(e) => edit(`fsa_tiers.${i}.prefixes`, parsePrefixes(e.target.value))}
                />
              </Field>
              <label className="flex items-center gap-2 pb-2 text-sm">
                <input
                  type="checkbox"
                  disabled={!canEdit}
                  checked={t.same_day !== false}
                  onChange={(e) => edit(`fsa_tiers.${i}.same_day`, e.target.checked)}
                />
                Same-day allowed
              </label>
              <Field label="Extra delivery days">
                <Input
                  type="number"
                  min="0"
                  max="7"
                  disabled={!canEdit}
                  value={String(t.extra_days ?? 0)}
                  onChange={(e) => edit(`fsa_tiers.${i}.extra_days`, wholeNumber(e.target.value))}
                />
              </Field>
              {canEdit ? (
                <Button
                  variant="outline"
                  onClick={() =>
                    edit(
                      "fsa_tiers",
                      tiers.filter((_, j) => j !== i)
                    )
                  }
                >
                  Remove
                </Button>
              ) : null}
            </div>
          ))}
          {canEdit ? (
            <Button
              variant="outline"
              onClick={() =>
                edit("fsa_tiers", [
                  ...tiers,
                  { name: `tier${tiers.length + 1}`, prefixes: [], same_day: false, extra_days: 0 },
                ])
              }
            >
              Add FSA tier
            </Button>
          ) : null}
        </div>
      </SettingsCard>

      <SettingsCard
        title="What buyers see"
        description="Service name and description on the Shopify checkout line. Use {cutoff}, {start}, {end}, {weekday}."
      >
        <div className="space-y-2">
          {SERVICE_KINDS.map(({ key, label }) => (
            <div key={key} className="grid gap-2 sm:grid-cols-2">
              <Field label={`${label}: name`}>
                <Input
                  disabled={!canEdit}
                  value={String(getPath(cfg, `services.${key}.name`) ?? "")}
                  onChange={(e) => edit(`services.${key}.name`, e.target.value)}
                />
              </Field>
              <Field label={`${label}: description`}>
                <Input
                  disabled={!canEdit}
                  value={String(getPath(cfg, `services.${key}.description`) ?? "")}
                  onChange={(e) => edit(`services.${key}.description`, e.target.value)}
                />
              </Field>
            </div>
          ))}
        </div>
      </SettingsCard>

      {canEdit && (
        <div className="flex flex-wrap items-end gap-3">
          <Field label="Change reason (audited)">
            <Input value={reason} onChange={(e) => setReason(e.target.value)} />
          </Field>
          <Button disabled={!dirty || saving} onClick={() => void save()}>
            Save delivery promise
          </Button>
          {problems.length ? <p className="text-sm text-red-600">{problems[0]}</p> : null}
        </div>
      )}
    </div>
  );
}
