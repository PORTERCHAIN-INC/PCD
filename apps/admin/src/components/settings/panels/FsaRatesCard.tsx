"use client";

import { useMemo, useState } from "react";
import { Pencil, Plus, Search, Trash2, X } from "lucide-react";
import { Button, EmptyState, Field, Input, Select } from "@/components/crm/primitives";
import { TableSkeleton } from "@porterchain/ui/loading";
import { useApiData } from "@/hooks/useApiData";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { merchants as merchantsApi } from "@/lib/merchants";
import { fsaRates, normalizeFsa, type FsaRate, type FsaRateInput } from "@/lib/pricing-fsa";
import type { VehicleClassConfig } from "@/lib/settings";
import { BindingBadge, SettingsCard } from "../ui/SettingsPrimitives";

const ANY = "";

const BLANK: FsaRateInput = {
  dest_fsa: "",
  flat_cents: 0,
  merchant_id: null,
  origin_fsa: null,
  vehicle_class: null,
  includes_location_fees: true,
  label: null,
  is_active: true,
  config: null,
};

function dollars(cents: number): string {
  return (cents / 100).toFixed(2);
}

/** Parse lines like `M5V,45.00` or `M5V,30,T1` into rate inputs. */
function parseBulkLines(text: string, merchantId?: string): FsaRateInput[] {
  const out: FsaRateInput[] = [];
  for (const raw of text.split(/\n+/)) {
    const line = raw.trim();
    if (!line || line.startsWith("#")) continue;
    const parts = line.split(/[,\t ]+/).filter(Boolean);
    if (parts.length < 2) continue;
    const dest = normalizeFsa(parts[0] || "");
    const price = Number(parts[1]);
    if (!dest || !Number.isFinite(price) || price < 0) continue;
    const tier = parts[2]?.trim();
    out.push({
      ...BLANK,
      dest_fsa: dest,
      flat_cents: Math.round(price * 100),
      merchant_id: merchantId ?? null,
      config: tier ? { tier } : null,
    });
  }
  return out;
}

/** Draft form state — prices are edited in dollars, stored in cents. */
type Draft = Omit<FsaRateInput, "flat_cents" | "config"> & {
  price: string;
  tier: string;
};

function toDraft(rate?: FsaRate): Draft {
  const base = rate ?? BLANK;
  const cfg = (base.config || {}) as Record<string, unknown>;
  return {
    dest_fsa: base.dest_fsa,
    price: rate ? dollars(rate.flat_cents) : "",
    merchant_id: base.merchant_id,
    origin_fsa: base.origin_fsa,
    vehicle_class: base.vehicle_class,
    includes_location_fees: base.includes_location_fees,
    label: base.label,
    is_active: base.is_active,
    tier: typeof cfg.tier === "string" ? cfg.tier : "",
  };
}

export default function FsaRatesCard({
  vehicleCatalog = [],
  merchantId,
  embedded = false,
  onChanged,
}: {
  vehicleCatalog?: VehicleClassConfig[];
  /** When set, new rates belong to this merchant and the list is filtered to them. */
  merchantId?: string;
  embedded?: boolean;
  onChanged?: () => void;
}) {
  const { getApiToken } = useAdminAuth();
  const { data, loading, error, refetch } = useApiData<FsaRate[]>(
    (token) => fsaRates.list(token, merchantId),
    [merchantId ?? "all"],
    { key: `pricing-fsa-rates-${merchantId ?? "all"}` }
  );
  const { data: gap, refetch: refetchGap } = useApiData(
    (token) => fsaRates.coverageGap(token, merchantId),
    [merchantId ?? "platform"],
    { key: `pricing-fsa-gap-${merchantId ?? "platform"}`, staleTime: 60_000 }
  );
  const { data: merchantList } = useApiData((token) => merchantsApi.list(token), [], {
    key: "pricing-fsa-merchants",
    staleTime: 300_000,
    enabled: !merchantId,
  });

  const [draft, setDraft] = useState<Draft | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [bulkText, setBulkText] = useState("");
  const [showBulk, setShowBulk] = useState(false);
  const [testDest, setTestDest] = useState("");
  const [testOrigin, setTestOrigin] = useState("");
  const [testMerchant, setTestMerchant] = useState("");
  const [testResult, setTestResult] = useState<string | null>(null);

  const rates = data ?? [];
  const merchantNames = useMemo(() => {
    const map = new Map<string, string>();
    for (const m of merchantList ?? []) map.set(m.id, m.company_name);
    return map;
  }, [merchantList]);
  const vehicleLabels = useMemo(
    () => Object.fromEntries(vehicleCatalog.map((v) => [v.id, v.label])),
    [vehicleCatalog]
  );

  function openNew() {
    setEditingId(null);
    setDraft(toDraft(undefined));
    if (merchantId) {
      setDraft((d) => (d ? { ...d, merchant_id: merchantId } : d));
    }
    setMessage(null);
  }

  function openEdit(rate: FsaRate) {
    setEditingId(rate.id);
    setDraft(toDraft(rate));
    setMessage(null);
  }

  function close() {
    setDraft(null);
    setEditingId(null);
  }

  async function save() {
    if (!draft) return;
    const dest = normalizeFsa(draft.dest_fsa);
    if (!dest) {
      setMessage("Destination FSA must look like M5V — a letter, a digit, then a letter.");
      return;
    }
    if (draft.origin_fsa && !normalizeFsa(draft.origin_fsa)) {
      setMessage("Origin FSA must look like L4W, or be left blank for any origin.");
      return;
    }
    const cents = Math.round(Number(draft.price) * 100);
    if (!Number.isFinite(cents) || cents < 0) {
      setMessage("Enter a price of $0.00 or more.");
      return;
    }

    const body: FsaRateInput = {
      dest_fsa: dest,
      flat_cents: cents,
      merchant_id: merchantId ?? draft.merchant_id ?? null,
      origin_fsa: draft.origin_fsa ? normalizeFsa(draft.origin_fsa) : null,
      vehicle_class: draft.vehicle_class || null,
      includes_location_fees: draft.includes_location_fees,
      label: draft.label?.trim() || null,
      is_active: draft.is_active,
      config: draft.tier.trim() ? { tier: draft.tier.trim() } : {},
    };

    setBusy(true);
    try {
      const token = await getApiToken();
      if (editingId) await fsaRates.update(token, editingId, body);
      else await fsaRates.create(token, body);
      close();
      await refetch();
      await refetchGap();
      onChanged?.();
      setMessage(editingId ? "Rate updated." : "Rate added — quotes use it immediately.");
    } catch (e) {
      const detail = e instanceof Error ? e.message : "Save failed";
      setMessage(
        detail.includes("already_exists")
          ? "A rate already covers that exact combination of merchant, origin, destination and vehicle."
          : detail.includes("out_of_gta150_tile")
            ? "That FSA is outside the GTA ±150 km tile (e.g. Ottawa K*). Use an in-tile FSA or distance pricing."
            : detail
      );
    } finally {
      setBusy(false);
    }
  }

  async function runBulk() {
    const parsed = parseBulkLines(bulkText, merchantId);
    if (!parsed.length) {
      setMessage("Paste lines like M5V,45.00 or M5V,30,T1 (FSA + CAD + optional tier).");
      return;
    }
    setBusy(true);
    try {
      const token = await getApiToken();
      const result = await fsaRates.bulk(token, parsed, merchantId ?? null);
      setBulkText("");
      setShowBulk(false);
      await refetch();
      await refetchGap();
      onChanged?.();
      setMessage(
        `Bulk: ${result.created} created, ${result.updated} updated` +
          (result.error_count ? `, ${result.error_count} rejected (out-of-tile or invalid).` : ".")
      );
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Bulk upload failed");
    } finally {
      setBusy(false);
    }
  }

  async function remove(rate: FsaRate) {
    const where = rate.origin_fsa ? `${rate.origin_fsa} to ${rate.dest_fsa}` : rate.dest_fsa;
    if (!window.confirm(`Delete the $${dollars(rate.flat_cents)} rate for ${where}?`)) return;
    setBusy(true);
    try {
      await fsaRates.remove(await getApiToken(), rate.id);
      await refetch();
      onChanged?.();
      setMessage("Rate deleted.");
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Delete failed");
    } finally {
      setBusy(false);
    }
  }

  async function runTest() {
    const dest = normalizeFsa(testDest);
    if (!dest) {
      setTestResult("Enter a destination postal code or FSA, like M5V 2T6.");
      return;
    }
    const origin = testOrigin ? normalizeFsa(testOrigin) : "";
    if (testOrigin && !origin) {
      setTestResult("The origin must look like L4W, or be left blank.");
      return;
    }
    try {
      const result = await fsaRates.quote(await getApiToken(), {
        dest_fsa: dest,
        // Lane rates only match when the origin is supplied, so a
        // destination-only check would wrongly report "no rate".
        ...(origin ? { origin_fsa: origin } : {}),
        ...(merchantId || testMerchant ? { merchant_id: merchantId || testMerchant } : {}),
      });
      const trip = origin ? `${origin} to ${dest}` : `anywhere to ${dest}`;
      if (!result.metadata.matched) {
        setTestResult(
          `No rate covers ${trip} — this trip is priced by the distance matrix instead.`
        );
        return;
      }
      const scope = result.metadata.merchant_scoped
        ? "a merchant-specific rate"
        : "a rate that applies to all merchants";
      const fees = result.metadata.includes_location_fees
        ? "all-in"
        : "plus any downtown or upper-zone fee";
      setTestResult(`${trip} matches ${scope}: $${dollars(result.total_cents)} ${fees}.`);
    } catch (e) {
      setTestResult(e instanceof Error ? e.message : "Lookup failed");
    }
  }

  return (
    <SettingsCard
      title={merchantId ? "FSA rates for this merchant" : "FSA flat rates"}
      description={
        merchantId
          ? "Rates added here apply only to this merchant. A matching rate replaces the distance charge."
          : "Fixed prices by postal-code area. A matching rate replaces the distance charge for that trip."
      }
      action={
        <div className="flex items-center gap-2">
          {!embedded && <BindingBadge effect="wired" />}
          <Button variant="outline" onClick={() => setShowBulk((v) => !v)} disabled={busy}>
            Bulk paste
          </Button>
          <Button variant="primary" onClick={openNew} disabled={busy}>
            <Plus className="h-4 w-4" /> Add rate
          </Button>
        </div>
      }
    >
      <p className="mb-4 text-xs text-muted">
        Checked after merchant contracts and before the GTA vehicle matrix. Leaving merchant, origin
        or vehicle blank means the rate applies to all of them; when several rates match, the most
        specific one wins. Destinations must be in the GTA ±150 km tile — unrated in-tile FSAs fall
        to Valhalla distance.
      </p>

      {gap && (
        <p className="mb-3 rounded-xl border border-primary/10 bg-gray-bg/50 px-3 py-2 text-xs text-primary">
          GTA150 gap ({gap.scope}): {gap.rated_in_tile_count}/{gap.tile_fsa_count} in-tile FSAs
          priced · {gap.missing_rate_count} unrated
          {gap.extra_out_of_tile_count > 0
            ? ` · ${gap.extra_out_of_tile_count} out-of-tile rows (legacy)`
            : ""}
          {gap.missing_sample?.length
            ? ` · sample missing: ${gap.missing_sample.slice(0, 8).join(", ")}`
            : ""}
        </p>
      )}

      {showBulk && (
        <div className="mb-4 rounded-xl border border-secondary/30 bg-secondary/5 p-4">
          <Field
            label="Bulk FSA flats"
            hint="One per line: M5V,45.00 or M5V,30,T1 — out-of-tile codes are rejected"
          >
            <textarea
              className="min-h-[96px] w-full rounded-lg border border-primary/15 bg-white px-3 py-2 text-sm"
              value={bulkText}
              placeholder={"M5V,30,T1\nL4W,45,T2"}
              onChange={(e) => setBulkText(e.target.value)}
            />
          </Field>
          <div className="mt-2 flex gap-2">
            <Button variant="primary" onClick={() => void runBulk()} disabled={busy}>
              Upload
            </Button>
            <Button variant="outline" onClick={() => setShowBulk(false)} disabled={busy}>
              Cancel
            </Button>
          </div>
        </div>
      )}

      {message && <p className="mb-3 text-sm text-secondary">{message}</p>}
      {error && <p className="mb-3 text-sm text-red-700">{error}</p>}

      {draft && (
        <div className="mb-4 rounded-xl border border-secondary/30 bg-secondary/5 p-4">
          <div className="mb-3 flex items-center justify-between">
            <h4 className="text-sm font-semibold text-primary">
              {editingId ? "Edit rate" : "New rate"}
            </h4>
            <button type="button" onClick={close} className="text-muted hover:text-primary">
              <X className="h-4 w-4" />
            </button>
          </div>

          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <Field label="Deliver to FSA" hint="Required — e.g. M5V">
              <Input
                value={draft.dest_fsa}
                placeholder="M5V"
                maxLength={7}
                onChange={(e) => setDraft({ ...draft, dest_fsa: e.target.value })}
              />
            </Field>
            <Field label="Price (CAD)" hint="What the customer pays for the trip">
              <Input
                type="number"
                step="0.01"
                min="0"
                value={draft.price}
                placeholder="18.00"
                onChange={(e) => setDraft({ ...draft, price: e.target.value })}
              />
            </Field>
            <Field label="Tier" hint="For route minimums — e.g. T1">
              <Input
                value={draft.tier}
                placeholder="T1"
                maxLength={8}
                onChange={(e) => setDraft({ ...draft, tier: e.target.value })}
              />
            </Field>
            <Field label="Pick up from FSA" hint="Blank = any origin">
              <Input
                value={draft.origin_fsa ?? ""}
                placeholder="Any"
                maxLength={7}
                onChange={(e) => setDraft({ ...draft, origin_fsa: e.target.value || null })}
              />
            </Field>
            {!merchantId && (
              <Field label="Merchant" hint="Blank = every merchant">
                <Select
                  value={draft.merchant_id ?? ANY}
                  onChange={(e) => setDraft({ ...draft, merchant_id: e.target.value || null })}
                >
                  <option value={ANY}>All merchants</option>
                  {(merchantList ?? []).map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.company_name}
                    </option>
                  ))}
                </Select>
              </Field>
            )}
            <Field label="Vehicle class" hint="Blank = every vehicle">
              <Select
                value={draft.vehicle_class ?? ANY}
                onChange={(e) => setDraft({ ...draft, vehicle_class: e.target.value || null })}
              >
                <option value={ANY}>All vehicles</option>
                {vehicleCatalog.map((v) => (
                  <option key={v.id} value={v.id}>
                    {v.label}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Label" hint="Shown on the quote line">
              <Input
                value={draft.label ?? ""}
                placeholder="e.g. Mississauga to downtown"
                onChange={(e) => setDraft({ ...draft, label: e.target.value || null })}
              />
            </Field>
          </div>

          <div className="mt-3 space-y-2">
            <label className="flex items-start gap-2 text-sm text-primary">
              <input
                type="checkbox"
                className="mt-1"
                checked={draft.includes_location_fees}
                onChange={(e) => setDraft({ ...draft, includes_location_fees: e.target.checked })}
              />
              <span>
                Price is all-in
                <span className="block text-xs text-muted">
                  Downtown and upper-zone surcharges are already covered. Uncheck to add them on top
                  of this rate.
                </span>
              </span>
            </label>
            <label className="flex items-center gap-2 text-sm text-primary">
              <input
                type="checkbox"
                checked={draft.is_active}
                onChange={(e) => setDraft({ ...draft, is_active: e.target.checked })}
              />
              Active
            </label>
          </div>

          <div className="mt-4 flex gap-2">
            <Button variant="primary" onClick={() => void save()} disabled={busy}>
              {busy ? "Saving…" : editingId ? "Save changes" : "Add rate"}
            </Button>
            <Button variant="outline" onClick={close}>
              Cancel
            </Button>
          </div>
        </div>
      )}

      {loading ? (
        <TableSkeleton rows={6} />
      ) : rates.length === 0 ? (
        <EmptyState
          title="No FSA rates yet"
          hint="Every quote is priced by distance. Add a rate to charge a fixed price into a postal-code area."
        />
      ) : (
        <div className="ops-table-scroll">
          <table className="w-full min-w-[40rem] text-left text-sm">
            <thead>
              <tr className="border-b border-primary/10 text-xs uppercase text-muted">
                <th className="py-2 pr-3">From</th>
                <th className="py-2 pr-3">To</th>
                <th className="py-2 pr-3">Price</th>
                <th className="py-2 pr-3">Tier</th>
                {!merchantId && <th className="py-2 pr-3">Merchant</th>}
                <th className="py-2 pr-3">Vehicle</th>
                <th className="py-2 pr-3">All-in</th>
                <th className="py-2 pr-3">Status</th>
                <th className="py-2" />
              </tr>
            </thead>
            <tbody>
              {rates.map((rate) => (
                <tr key={rate.id} className="border-b border-primary/5">
                  <td className="py-2 pr-3 text-muted">{rate.origin_fsa ?? "Any"}</td>
                  <td className="py-2 pr-3 font-medium">{rate.dest_fsa}</td>
                  <td className="py-2 pr-3 tabular-nums">${dollars(rate.flat_cents)}</td>
                  <td className="py-2 pr-3 text-muted">
                    {typeof (rate.config as { tier?: string } | null | undefined)?.tier === "string"
                      ? (rate.config as { tier: string }).tier
                      : "—"}
                  </td>
                  {!merchantId && (
                    <td className="py-2 pr-3">
                      {rate.merchant_id
                        ? (merchantNames.get(rate.merchant_id) ?? rate.merchant_id)
                        : "All merchants"}
                    </td>
                  )}
                  <td className="py-2 pr-3">
                    {rate.vehicle_class
                      ? (vehicleLabels[rate.vehicle_class] ?? rate.vehicle_class)
                      : "All vehicles"}
                  </td>
                  <td className="py-2 pr-3">{rate.includes_location_fees ? "Yes" : "No"}</td>
                  <td className="py-2 pr-3">
                    {rate.is_active ? (
                      <span className="text-emerald-700">Active</span>
                    ) : (
                      <span className="text-muted">Paused</span>
                    )}
                  </td>
                  <td className="py-2">
                    <div className="flex justify-end gap-1">
                      <button
                        type="button"
                        title="Edit"
                        onClick={() => openEdit(rate)}
                        className="rounded-lg p-1.5 text-muted hover:bg-gray-bg hover:text-primary"
                      >
                        <Pencil className="h-4 w-4" />
                      </button>
                      <button
                        type="button"
                        title="Delete"
                        onClick={() => void remove(rate)}
                        className="rounded-lg p-1.5 text-muted hover:bg-red-50 hover:text-red-700"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="mt-5 border-t border-primary/10 pt-4">
        <p className="mb-2 text-xs font-medium text-primary/70">
          Check which rate a trip would get
        </p>
        <div className="flex flex-wrap items-end gap-2">
          <Input
            value={testOrigin}
            placeholder="From (optional)"
            className="max-w-[160px]"
            onChange={(e) => setTestOrigin(e.target.value)}
          />
          <Input
            value={testDest}
            placeholder="To — M5V 2T6"
            className="max-w-[160px]"
            onChange={(e) => setTestDest(e.target.value)}
          />
          {!merchantId && (
            <Select
              value={testMerchant}
              className="max-w-[200px]"
              onChange={(e) => setTestMerchant(e.target.value)}
            >
              <option value="">Any merchant</option>
              {(merchantList ?? []).map((m) => (
                <option key={m.id} value={m.id}>
                  {m.company_name}
                </option>
              ))}
            </Select>
          )}
          <Button variant="outline" onClick={() => void runTest()}>
            <Search className="h-4 w-4" /> Check
          </Button>
        </div>
        {testResult && <p className="mt-2 text-sm text-secondary">{testResult}</p>}
      </div>
    </SettingsCard>
  );
}
