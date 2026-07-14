"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, Plus, RefreshCw } from "lucide-react";
import { cn, formatCents } from "@porterchain/ui/utils";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import PricingTariffsGrid from "@/components/pricing/PricingTariffsGrid";
import PricingSimulator from "@/components/pricing/PricingSimulator";
import RateCardEditor from "@/components/pricing/RateCardEditor";
import { Button, Spinner } from "@/components/crm/primitives";
import {
  pricingApi,
  RULE_STATUSES,
  TARIFF_TYPES,
  VEHICLE_CLASSES,
  type TariffFilters,
} from "@/lib/pricing";
import { relativeTime } from "@/lib/crmFormat";

type Tab =
  "ratecard" | "rules" | "zones" | "contracts" | "promotions" | "tax" | "simulator" | "reports";

export default function PricingPage() {
  const { getApiToken, isLoaded, isSignedIn } = useAdminAuth();
  const qc = useQueryClient();
  const [tab, setTab] = useState<Tab>("ratecard");
  const [filters, setFilters] = useState<TariffFilters>({});

  const enabled = isLoaded && (isSignedIn || process.env.NODE_ENV === "development");

  const { data: dashboard } = useQuery({
    queryKey: ["pricing-dashboard"],
    enabled,
    queryFn: async () => pricingApi.dashboard(await getApiToken()),
  });

  const { data: rateCard, isLoading: rateCardLoading } = useQuery({
    queryKey: ["pricing-rate-card"],
    enabled: enabled && tab === "ratecard",
    queryFn: async () => pricingApi.rateCard(await getApiToken()),
  });

  const {
    data: tariffs = [],
    isLoading,
    refetch,
  } = useQuery({
    queryKey: ["pricing-tariffs", JSON.stringify(filters)],
    enabled: enabled && tab === "rules",
    queryFn: async () => pricingApi.tariffs(await getApiToken(), filters),
  });

  const { data: zones = [] } = useQuery({
    queryKey: ["pricing-zones"],
    enabled: enabled && tab === "zones",
    queryFn: async () => pricingApi.zones(await getApiToken()),
  });

  const { data: contracts = [] } = useQuery({
    queryKey: ["pricing-contracts"],
    enabled: enabled && tab === "contracts",
    queryFn: async () => pricingApi.contracts(await getApiToken()),
  });

  const { data: promotions = [] } = useQuery({
    queryKey: ["pricing-promotions"],
    enabled: enabled && tab === "promotions",
    queryFn: async () => pricingApi.promotions(await getApiToken()),
  });

  const { data: tax } = useQuery({
    queryKey: ["pricing-tax"],
    enabled: enabled && tab === "tax",
    queryFn: async () => pricingApi.tax(await getApiToken()),
  });

  const { data: fuel } = useQuery({
    queryKey: ["pricing-fuel"],
    enabled: enabled && tab === "tax",
    queryFn: async () => pricingApi.fuel(await getApiToken()),
  });

  const { data: reports } = useQuery({
    queryKey: ["pricing-reports"],
    enabled: enabled && tab === "reports",
    queryFn: async () => pricingApi.reports(await getApiToken()),
  });

  const { data: conflicts = [] } = useQuery({
    queryKey: ["pricing-conflicts"],
    enabled,
    queryFn: async () => pricingApi.conflicts(await getApiToken()),
  });

  async function createRule() {
    const name = prompt("Rule name");
    const type = prompt(`Tariff type:\n${TARIFF_TYPES.join(", ")}`);
    if (!name || !type) return;
    const token = await getApiToken();
    await pricingApi.createTariff(token, {
      name,
      tariff_type: type,
      vehicle_class: "sedan",
      base_cents: 1999,
      per_km_cents: 95,
    });
    await qc.invalidateQueries({ queryKey: ["pricing-tariffs"] });
    await qc.invalidateQueries({ queryKey: ["pricing-dashboard"] });
    void refetch();
  }

  async function publishRule(id: string) {
    const token = await getApiToken();
    await pricingApi.publishTariff(token, id);
    void refetch();
  }

  const TABS: { id: Tab; label: string }[] = [
    { id: "ratecard", label: "Rate card" },
    { id: "rules", label: "Pricing rules" },
    { id: "zones", label: "Zones" },
    { id: "contracts", label: "Contracts" },
    { id: "promotions", label: "Promotions" },
    { id: "tax", label: "Tax & fuel" },
    { id: "simulator", label: "Simulator" },
    { id: "reports", label: "Reports" },
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-primary">Pricing Engine</h1>
          <p className="text-sm text-muted">
            Manage rules, contracts, zones, and simulate quotes — server authoritative
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => void refetch()}>
            <RefreshCw className="h-4 w-4" /> Refresh
          </Button>
          {tab === "rules" && (
            <Button variant="primary" onClick={() => void createRule()}>
              <Plus className="h-4 w-4" /> New rule
            </Button>
          )}
        </div>
      </div>

      {dashboard && (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-6">
          <Kpi label="Active rules" value={dashboard.active_pricing_rules} />
          <Kpi label="Contracts" value={dashboard.merchant_contracts} />
          <Kpi label="Vehicle rules" value={dashboard.vehicle_pricing_rules} />
          <Kpi label="Zones" value={dashboard.zone_pricing_rules} />
          <Kpi label="Distance rules" value={dashboard.distance_pricing_rules} />
          <Kpi label="Weight rules" value={dashboard.weight_pricing_rules} />
          <Kpi label="Fuel %" value={`${dashboard.fuel_surcharge_percent}%`} />
          <Kpi label="HST %" value={`${dashboard.tax_hst_percent}%`} />
          <Kpi label="Coupons" value={dashboard.active_coupons} />
          <Kpi label="Forecast" value={formatCents(dashboard.revenue_forecast_cents)} />
          <Kpi
            label="Conflicts"
            value={dashboard.conflict_count}
            alert={dashboard.conflict_count > 0}
          />
        </div>
      )}

      {conflicts.length > 0 || dashboard?.conflict_count ? (
        <div className="flex items-start gap-2 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>
            {conflicts.length || dashboard?.conflict_count} pricing rule conflict(s) detected —
            review duplicate vehicle/zone/merchant combinations.
          </span>
        </div>
      ) : null}

      {dashboard?.recent_changes?.length ? (
        <div className="rounded-xl border border-primary/10 bg-white px-4 py-3">
          <p className="text-xs font-bold uppercase text-muted">Recently changed</p>
          <ul className="mt-2 space-y-1 text-sm">
            {dashboard.recent_changes.slice(0, 5).map((c, i) => (
              <li key={i} className="text-primary">
                {String(c.action)} · {c.created_at ? relativeTime(String(c.created_at)) : ""}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      <nav className="flex gap-1 overflow-x-auto border-b border-primary/10 pb-px">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setTab(t.id)}
            className={cn(
              "shrink-0 rounded-t-lg px-3 py-2 text-sm font-medium",
              tab === t.id
                ? "border border-b-0 border-primary/10 bg-white text-secondary"
                : "text-muted"
            )}
          >
            {t.label}
          </button>
        ))}
      </nav>

      <div className="rounded-2xl border border-primary/10 bg-white p-4">
        {tab === "ratecard" &&
          (rateCardLoading || !rateCard ? (
            <div className="flex justify-center py-12">
              <Spinner />
            </div>
          ) : (
            <RateCardEditor
              initial={rateCard}
              title="System rate card"
              subtitle="Edits apply to retail quotes and merchants without an override. Amounts in CAD cents unless marked %."
              onSave={async (card) => {
                const token = await getApiToken();
                await pricingApi.updateRateCard(token, card);
                await qc.invalidateQueries({ queryKey: ["pricing-rate-card"] });
                await qc.invalidateQueries({ queryKey: ["pricing-dashboard"] });
              }}
            />
          ))}

        {tab === "rules" && (
          <>
            <div className="mb-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
              <input
                placeholder="Search rules…"
                value={filters.search ?? ""}
                onChange={(e) => setFilters((f) => ({ ...f, search: e.target.value || undefined }))}
                className="rounded-xl border border-primary/10 px-3 py-2 text-sm sm:col-span-2 lg:col-span-1"
              />
              <select
                value={filters.tariff_type ?? ""}
                onChange={(e) =>
                  setFilters((f) => ({ ...f, tariff_type: e.target.value || undefined }))
                }
                className="w-full rounded-xl border border-primary/10 px-3 py-2 text-sm"
              >
                <option value="">All types</option>
                {TARIFF_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
              <select
                value={filters.vehicle_class ?? ""}
                onChange={(e) =>
                  setFilters((f) => ({ ...f, vehicle_class: e.target.value || undefined }))
                }
                className="w-full rounded-xl border border-primary/10 px-3 py-2 text-sm"
              >
                <option value="">All vehicles</option>
                {VEHICLE_CLASSES.map((v) => (
                  <option key={v} value={v}>
                    {v}
                  </option>
                ))}
              </select>
              <select
                value={filters.status ?? ""}
                onChange={(e) => setFilters((f) => ({ ...f, status: e.target.value || undefined }))}
                className="w-full rounded-xl border border-primary/10 px-3 py-2 text-sm"
              >
                <option value="">All statuses</option>
                {RULE_STATUSES.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </div>
            {isLoading ? (
              <div className="flex justify-center py-12">
                <Spinner />
              </div>
            ) : (
              <PricingTariffsGrid
                rows={tariffs}
                hideToolbar
                onPublish={(id) => void publishRule(id)}
              />
            )}
          </>
        )}

        {tab === "zones" && (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left text-muted">
                <th className="py-2">Code</th>
                <th>Name</th>
                <th>Multiplier</th>
                <th>Active</th>
              </tr>
            </thead>
            <tbody>
              {zones.map((z) => (
                <tr key={z.id} className="border-b border-primary/5">
                  <td className="py-2 font-mono">{z.code}</td>
                  <td>{z.name}</td>
                  <td>{z.multiplier}x</td>
                  <td>{z.is_active ? "Yes" : "No"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {tab === "contracts" && (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left text-muted">
                <th className="py-2">Merchant</th>
                <th>Contract</th>
                <th>Min commitment</th>
                <th>Active</th>
              </tr>
            </thead>
            <tbody>
              {contracts.map((c) => (
                <tr key={c.id} className="border-b border-primary/5">
                  <td className="py-2">{c.merchant_name || c.merchant_id}</td>
                  <td>{c.name}</td>
                  <td>{formatCents(c.minimum_monthly_commitment_cents)}</td>
                  <td>{c.is_active ? "Yes" : "No"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {tab === "promotions" && (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left text-muted">
                <th className="py-2">Code</th>
                <th>Type</th>
                <th>Discount</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {promotions.map((p) => (
                <tr key={p.id} className="border-b border-primary/5">
                  <td className="py-2 font-mono font-semibold">{p.code}</td>
                  <td>{p.promotion_type}</td>
                  <td>
                    {p.discount_percent
                      ? `${p.discount_percent}%`
                      : p.discount_cents
                        ? formatCents(p.discount_cents)
                        : "—"}
                  </td>
                  <td className="capitalize">{p.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {tab === "tax" && tax && fuel && (
          <div className="grid gap-6 md:grid-cols-2">
            <div>
              <h3 className="mb-3 font-semibold">Tax (HST/GST/PST)</h3>
              <p className="text-sm">
                HST: {String(tax.hst_percent)}% · Tax included: {tax.tax_included ? "Yes" : "No"}
              </p>
              <Button
                variant="outline"
                className="mt-3"
                onClick={async () => {
                  const hst = prompt("HST %", String(tax.hst_percent));
                  if (!hst) return;
                  const token = await getApiToken();
                  await pricingApi.updateTax(token, { ...tax, hst_percent: Number(hst) });
                  await qc.invalidateQueries({ queryKey: ["pricing-tax"] });
                }}
              >
                Update tax
              </Button>
            </div>
            <div>
              <h3 className="mb-3 font-semibold">Fuel surcharge</h3>
              <p className="text-sm">Surcharge: {String(fuel.surcharge_percent)}%</p>
              <Button
                variant="outline"
                className="mt-3"
                onClick={async () => {
                  const pct = prompt("Fuel surcharge %", String(fuel.surcharge_percent));
                  if (!pct) return;
                  const token = await getApiToken();
                  await pricingApi.updateFuel(token, { ...fuel, surcharge_percent: Number(pct) });
                  await qc.invalidateQueries({ queryKey: ["pricing-fuel"] });
                }}
              >
                Update fuel
              </Button>
            </div>
          </div>
        )}

        {tab === "simulator" && (
          <PricingSimulator
            onSimulate={async (body) => {
              const token = await getApiToken();
              return pricingApi.simulate(token, body);
            }}
          />
        )}

        {tab === "reports" && reports && (
          <div className="space-y-4 text-sm">
            <p>Avg order value: {formatCents(Number(reports.avg_order_value_cents || 0))}</p>
            <p>Pricing changes this month: {String(reports.pricing_changes_month)}</p>
            <p>Active contracts: {String(reports.active_contracts)}</p>
            <p>Active coupons: {String(reports.active_coupons)}</p>
            {Array.isArray(reports.rules_by_type) && (
              <ul className="mt-2 space-y-1">
                {(reports.rules_by_type as [string, number][]).map(([type, count]) => (
                  <li key={type}>
                    {type}: {count} rules
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function Kpi({ label, value, alert }: { label: string; value: string | number; alert?: boolean }) {
  return (
    <div
      className={cn(
        "rounded-xl border border-primary/10 bg-white px-3 py-2 shadow-sm",
        alert && "border-amber-200 bg-amber-50"
      )}
    >
      <p className="text-xs text-muted">{label}</p>
      <p className="text-lg font-bold text-primary">{value}</p>
    </div>
  );
}
