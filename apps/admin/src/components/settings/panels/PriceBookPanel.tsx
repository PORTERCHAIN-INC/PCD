"use client";

import { useEffect, useState } from "react";
import { Save } from "lucide-react";
import { Button, Field, Input, Select, Textarea } from "@/components/crm/primitives";
import { useOptionalAdminProfile } from "@/components/nav/AdminProfileContext";
import {
  asObject,
  centsToDollars,
  dollarsToCents,
  DRIVER_PAY_MODES,
  DRIVER_PAY_PLACEHOLDERS,
  getPath,
  isPlaceholder,
  PRICE_BOOK_PLACEHOLDERS,
  setPath,
  wholeNumber,
  type JsonObject,
} from "@/lib/price-book";
import { SettingsCard } from "../ui/SettingsPrimitives";

type Props = {
  bookData: unknown;
  driverPayData: unknown;
  saving?: boolean;
  onSaveBook: (value: JsonObject, reason: string) => Promise<void>;
  onSaveDriverPay: (value: JsonObject, reason: string) => Promise<void>;
};

function Example({ show }: { show: boolean }) {
  if (!show) return null;
  return (
    <span className="ml-1 rounded bg-amber-100 px-1.5 py-0.5 text-[10px] font-semibold uppercase text-amber-900">
      Example
    </span>
  );
}

function lbl(text: string, example: boolean): string {
  return example ? `${text} · EXAMPLE` : text;
}

/**
 * Global price book (merchant parcels, retail, dedicated vehicles) and the
 * driver pay plan. Saving bumps the price version; the API rejects non super
 * admins with 403, so the form is read-only for everyone else.
 */
export default function PriceBookPanel({
  bookData,
  driverPayData,
  saving,
  onSaveBook,
  onSaveDriverPay,
}: Props) {
  const profile = useOptionalAdminProfile();
  const canEdit = (profile?.role || "").toLowerCase() === "super_admin";
  const [book, setBook] = useState<JsonObject>(() => asObject(bookData));
  const [pay, setPay] = useState<JsonObject>(() => asObject(driverPayData));
  const [dirty, setDirty] = useState<"book" | "pay" | null>(null);
  const [reason, setReason] = useState("");
  const [toast, setToast] = useState<string | null>(null);

  useEffect(() => setBook(asObject(bookData)), [bookData]);
  useEffect(() => setPay(asObject(driverPayData)), [driverPayData]);

  const bp = (path: string) => isPlaceholder(path, PRICE_BOOK_PLACEHOLDERS);
  const dp = (path: string) => isPlaceholder(path, DRIVER_PAY_PLACEHOLDERS);

  function editBook(path: string, value: unknown) {
    setBook((b) => setPath(b, path, value));
    setDirty("book");
  }
  function editPay(path: string, value: unknown) {
    setPay((p) => setPath(p, path, value));
    setDirty("pay");
  }

  function money(path: string, src: JsonObject, edit: (p: string, v: unknown) => void) {
    return (
      <Input
        type="number"
        step="0.01"
        min="0"
        disabled={!canEdit}
        value={centsToDollars(getPath(src, path))}
        onChange={(e) => edit(path, dollarsToCents(e.target.value))}
      />
    );
  }
  function count(path: string, src: JsonObject, edit: (p: string, v: unknown) => void) {
    return (
      <Input
        type="number"
        min="0"
        disabled={!canEdit}
        value={String(getPath(src, path) ?? 0)}
        onChange={(e) => edit(path, wholeNumber(e.target.value))}
      />
    );
  }
  function toggle(path: string, label: string) {
    return (
      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          disabled={!canEdit}
          checked={Boolean(getPath(book, path))}
          onChange={(e) => editBook(path, e.target.checked)}
        />
        {label}
      </label>
    );
  }

  async function save() {
    if (!reason.trim()) {
      setToast("Change reason required for pricing");
      return;
    }
    try {
      if (dirty === "pay") await onSaveDriverPay(pay, reason.trim());
      else await onSaveBook(book, reason.trim());
      setDirty(null);
      setReason("");
      setToast("Saved — new price version stamped on quotes from now on");
    } catch (e) {
      setToast(e instanceof Error ? e.message : "Save failed");
    }
  }

  const tiers = Array.isArray(book.parcel_tiers) ? (book.parcel_tiers as JsonObject[]) : [];
  const handling = Array.isArray(getPath(book, "handling.tiers"))
    ? (getPath(book, "handling.tiers") as JsonObject[])
    : [];
  const vehicles = asObject(getPath(book, "dedicated.vehicles"));

  return (
    <div className="space-y-6">
      <p className="rounded-xl border border-primary/10 bg-primary/5 px-3 py-2 text-sm">
        Super admin only. {canEdit ? "" : "You can view these values; saving needs a super admin. "}
        Fields marked <Example show /> are placeholders waiting for a pricing decision. Every save
        is audited and bumps the price version stamped on each quote.
      </p>
      {toast && <p className="text-sm text-secondary">{toast}</p>}

      <SettingsCard
        title="Merchant parcels"
        description="Off by default. When on, merchants without a contract schedule pay per parcel by tier instead of the generic size tiers. Merchants can override in their pricing tab."
      >
        <div className="space-y-3">
          {toggle("merchant_parcels.enabled", "Use the price book for merchant parcels")}
          <div className="grid gap-3 sm:grid-cols-3">
            <Field label={lbl("Stop price, no FSA match (CAD)", bp("stop_price_cents"))}>
              {money("stop_price_cents", book, editBook)}
            </Field>
            <Field label={lbl("Minimum (CAD)", bp("minimum.cents"))}>
              {money("minimum.cents", book, editBook)}
            </Field>
            <Field label={lbl("Minimum applies", bp("minimum.mode"))}>
              <Select
                disabled={!canEdit}
                value={String(getPath(book, "minimum.mode") ?? "per_route")}
                onChange={(e) => editBook("minimum.mode", e.target.value)}
              >
                <option value="per_route">Per route</option>
                <option value="per_stop">Per stop</option>
              </Select>
            </Field>
          </div>
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="text-xs uppercase text-muted">
                <th className="py-1">
                  Parcels at stop
                  <Example show={bp("parcel_tiers")} />
                </th>
                <th className="py-1">Per parcel (CAD)</th>
                <th className="py-1">Custom quote</th>
              </tr>
            </thead>
            <tbody>
              {tiers.map((t, i) => (
                <tr key={i} className="border-t border-primary/5">
                  <td className="py-1">
                    {t.max_parcels == null ? "More" : `Up to ${String(t.max_parcels)}`}
                  </td>
                  <td className="py-1">
                    {money(`parcel_tiers.${i}.cents_per_parcel`, book, editBook)}
                  </td>
                  <td className="py-1">{t.custom_quote ? "Yes" : "No"}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="grid gap-3 sm:grid-cols-3">
            <Field label={lbl("Small parcel max (lb)", bp("small_parcel.max_lb"))}>
              {count("small_parcel.max_lb", book, editBook)}
            </Field>
            <Field label="Small parcels per group">
              {count("small_parcel.group_size", book, editBook)}
            </Field>
            <Field label={lbl("Small parcel charge", bp("small_parcel.charge_mode"))}>
              <Select
                disabled={!canEdit}
                value={String(getPath(book, "small_parcel.charge_mode") ?? "free")}
                onChange={(e) => editBook("small_parcel.charge_mode", e.target.value)}
              >
                <option value="free">Free</option>
                <option value="per_group">One parcel per group</option>
              </Select>
            </Field>
          </div>
          <p className="text-xs text-muted">
            Handling (per box, higher of weight or footprint):{" "}
            {handling
              .map(
                (h) =>
                  `${String(h.code)} ≤${String(h.max_weight)} lb +$${centsToDollars(h.surcharge_cents)}`
              )
              .join(" · ")}
            ; beyond = custom quote.
          </p>
          <div className="grid gap-3 sm:grid-cols-3">
            {handling.map((h, i) => (
              <Field key={String(h.code)} label={`${String(h.code)} surcharge (CAD)`}>
                {money(`handling.tiers.${i}.surcharge_cents`, book, editBook)}
              </Field>
            ))}
          </div>
        </div>
      </SettingsCard>

      <SettingsCard
        title="Retail single price"
        description="Off by default. One price for a retail delivery."
      >
        <div className="space-y-3">
          {toggle("retail.enabled", "Use the single retail price")}
          <div className="grid gap-3 sm:grid-cols-3">
            <Field label={lbl("Price (CAD)", bp("retail.fixed_price_cents"))}>
              {money("retail.fixed_price_cents", book, editBook)}
            </Field>
            <Field label={lbl("Parcels included", bp("retail.included_parcels"))}>
              {count("retail.included_parcels", book, editBook)}
            </Field>
            <Field label={lbl("Each extra parcel (CAD)", bp("retail.extra_parcel_cents"))}>
              {money("retail.extra_parcel_cents", book, editBook)}
            </Field>
          </div>
        </div>
      </SettingsCard>

      <SettingsCard
        title="Dedicated vehicle"
        description="Off by default. Booked by the hour or half-day block."
      >
        <div className="space-y-3">
          {toggle("dedicated.enabled", "Offer dedicated vehicles")}
          <div className="grid gap-3 sm:grid-cols-3">
            <Field label={lbl("Billing unit", bp("dedicated.unit"))}>
              <Select
                disabled={!canEdit}
                value={String(getPath(book, "dedicated.unit") ?? "half_day")}
                onChange={(e) => editBook("dedicated.unit", e.target.value)}
              >
                <option value="half_day">Half-day block</option>
                <option value="hour">Hour</option>
              </Select>
            </Field>
            <Field label="Block hours">{count("dedicated.block_hours", book, editBook)}</Field>
            <Field label="Minimum units">{count("dedicated.min_units", book, editBook)}</Field>
          </div>
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="text-xs uppercase text-muted">
                <th className="py-1">
                  Vehicle
                  <Example show={bp("dedicated.vehicles")} />
                </th>
                <th className="py-1">Hour (CAD)</th>
                <th className="py-1">Half-day (CAD)</th>
              </tr>
            </thead>
            <tbody>
              {Object.keys(vehicles).map((id) => (
                <tr key={id} className="border-t border-primary/5">
                  <td className="py-1 font-medium">{id}</td>
                  <td className="py-1">
                    {money(`dedicated.vehicles.${id}.hour_cents`, book, editBook)}
                  </td>
                  <td className="py-1">
                    {money(`dedicated.vehicles.${id}.half_day_cents`, book, editBook)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </SettingsCard>

      <SettingsCard
        title="Driver pay plan"
        description="Config only — payouts are not wired to this yet. $27/h and the 4 h block are decided."
      >
        <div className="grid gap-3 sm:grid-cols-3">
          <Field label="Pay mode">
            <Select
              disabled={!canEdit}
              value={String(pay.mode ?? "wave_block")}
              onChange={(e) => editPay("mode", e.target.value)}
            >
              {DRIVER_PAY_MODES.map((m) => (
                <option key={m} value={m}>
                  {m.replace("_", " ")}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Hourly (CAD)">{money("hourly_cents", pay, editPay)}</Field>
          <Field label="Minimum paid hours">{count("minimum_paid_hours", pay, editPay)}</Field>
          <Field label={lbl("Per stop (CAD)", dp("per_stop_cents"))}>
            {money("per_stop_cents", pay, editPay)}
          </Field>
          <Field label={lbl("Per pickup (CAD)", dp("per_pickup_cents"))}>
            {money("per_pickup_cents", pay, editPay)}
          </Field>
          <Field label={lbl("Per route (CAD)", dp("per_route_cents"))}>
            {money("per_route_cents", pay, editPay)}
          </Field>
          <Field label={lbl("Stops included per route", dp("route_included_stops"))}>
            {count("route_included_stops", pay, editPay)}
          </Field>
          <Field label={lbl("Extra route stop (CAD)", dp("route_extra_stop_cents"))}>
            {money("route_extra_stop_cents", pay, editPay)}
          </Field>
          <Field label="Wave block hours">{count("wave_block.block_hours", pay, editPay)}</Field>
          <Field label={lbl("Wave block pay (CAD)", dp("wave_block.block_cents"))}>
            {money("wave_block.block_cents", pay, editPay)}
          </Field>
          <Field label={lbl("Stops included per block", dp("wave_block.included_stops"))}>
            {count("wave_block.included_stops", pay, editPay)}
          </Field>
          <Field label={lbl("Extra block stop (CAD)", dp("wave_block.extra_stop_cents"))}>
            {money("wave_block.extra_stop_cents", pay, editPay)}
          </Field>
        </div>
      </SettingsCard>

      {canEdit && (
        <div className="space-y-2">
          <label className="block text-sm">
            <span className="text-xs font-medium text-muted">Change reason (required)</span>
            <Textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              rows={2}
              className="mt-1"
              placeholder="e.g. Approved v3 parcel tiers"
            />
          </label>
          <Button variant="primary" disabled={!dirty || saving} onClick={() => void save()}>
            <Save className="h-4 w-4" />{" "}
            {saving ? "Saving…" : dirty === "pay" ? "Save driver pay" : "Save price book"}
          </Button>
        </div>
      )}
    </div>
  );
}
