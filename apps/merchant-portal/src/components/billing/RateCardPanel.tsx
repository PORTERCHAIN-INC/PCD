"use client";

import { useQuery } from "@tanstack/react-query";
import { PageSkeleton } from "@porterchain/ui/loading";
import { billingApi } from "@/lib/billing";
import { COMPACT_SCHEDULE_DEFAULTS, pricingModelLabel } from "@porterchain/types";
import type { MerchantRateCard } from "@/lib/rate-card";
import { formatCents } from "@/lib/utils";

export function RateCardPanel({
  getToken,
  orgId,
}: {
  getToken: () => Promise<string>;
  orgId?: string;
}) {
  const { data: card, error: queryError } = useQuery({
    queryKey: ["merchant-rate-card", orgId ?? null],
    queryFn: async () => billingApi.rateCard(await getToken(), orgId),
  });
  const error = queryError instanceof Error ? queryError.message : null;

  const isFsa = card?.pricing_model === "fsa";

  return (
    <section className="rounded-2xl border border-primary/10 bg-white p-6">
      <h2 className="font-semibold text-primary">Your rates</h2>
      {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
      {!card && !error && <PageSkeleton rows={3} />}
      {card && (
        <div className="mt-4 space-y-4 text-sm">
          <p>
            <span className="text-muted">How we price: </span>
            {pricingModelLabel(card.pricing_model)}
          </p>
          <p className="text-muted">{card.what_wins}</p>

          {isFsa ? (
            <>
              <div className="rounded-xl border border-primary/10 bg-gray-bg/30 px-4 py-3">
                <h3 className="font-medium text-primary">Ontario FSA flats</h3>
                <p className="mt-1 text-muted">
                  Checkout and portal quotes use your FSA schedule (T1 / T2 / T3 by destination
                  postal). Distance tables below are fallback only when your schedule allows it.
                </p>
                <dl className="mt-3 grid gap-2 sm:grid-cols-2">
                  <div className="flex justify-between gap-4">
                    <dt className="text-muted">Your FSA rows</dt>
                    <dd>
                      {card.fsa_rate_count} · {card.platform_fsa_rate_count} platform defaults
                    </dd>
                  </div>
                  {card.schedule ? (
                    <>
                      <div className="flex justify-between gap-4">
                        <dt className="text-muted">Outside FSA</dt>
                        <dd>
                          {card.schedule.fsa_miss === "refuse"
                            ? "Refuse quote"
                            : "Distance fallback"}
                        </dd>
                      </div>
                      <div className="flex justify-between gap-4">
                        <dt className="text-muted">Origin pickup</dt>
                        <dd>
                          {card.schedule.origin_pickup_cents > 0
                            ? formatCents(card.schedule.origin_pickup_cents)
                            : "—"}
                        </dd>
                      </div>
                      <div className="flex justify-between gap-4 sm:col-span-2">
                        <dt className="text-muted">Route minimums</dt>
                        <dd>
                          {Object.keys(card.schedule.route_minimums_cents || {}).length
                            ? Object.entries(card.schedule.route_minimums_cents)
                                .map(([k, v]) => `${k} ${formatCents(v)}`)
                                .join(" · ")
                            : "—"}
                        </dd>
                      </div>
                      {card.schedule.compact?.enabled ? (
                        <div className="sm:col-span-2 space-y-1">
                          <p className="font-medium text-primary">Compact banding</p>
                          <p className="text-muted">
                            {(card.schedule.compact.vehicle_classes || []).join(", ") ||
                              "Compact vehicles"}{" "}
                            ·{" "}
                            {card.schedule.compact.parcels_per_stop ??
                              COMPACT_SCHEDULE_DEFAULTS.parcels_per_stop}{" "}
                            parcels / stop · min{" "}
                            {formatCents(card.schedule.compact.route_minimum_cents)}
                          </p>
                          {(card.schedule.compact.stop_rates_cents || []).length > 0 ? (
                            <ul className="list-disc pl-5 text-muted">
                              {card.schedule.compact.stop_rates_cents!.map((band, i) => (
                                <li key={i}>
                                  {formatCents(band.cents)}
                                  {band.max_stops != null
                                    ? ` up to ${band.max_stops} stops`
                                    : " open-ended"}
                                </li>
                              ))}
                            </ul>
                          ) : null}
                        </div>
                      ) : null}
                    </>
                  ) : null}
                </dl>
              </div>
              {card.size_tiers.length > 0 && (
                <div>
                  <h3 className="font-medium text-primary">Handling / size</h3>
                  <ul className="mt-2 list-disc space-y-1 pl-5 text-muted">
                    {card.size_tiers.map((t, i) => (
                      <li key={i}>
                        {t.label || "Size rule"} — {formatCents(t.surcharge_cents)}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              <dl className="grid gap-2 sm:grid-cols-2">
                <div className="flex justify-between gap-4">
                  <dt className="text-muted">Fuel</dt>
                  <dd>{card.fuel_surcharge_percent}%</dd>
                </div>
                <div className="flex justify-between gap-4">
                  <dt className="text-muted">HST</dt>
                  <dd>
                    {card.tax.hst_percent}%{card.tax.tax_included ? " (included)" : ""}
                  </dd>
                </div>
              </dl>
              {card.schedule?.fsa_miss !== "refuse" && card.vehicles.length > 0 ? (
                <details className="rounded-xl border border-primary/10 px-4 py-3">
                  <summary className="cursor-pointer font-medium text-primary">
                    Distance fallback table
                  </summary>
                  <p className="mt-2 text-muted">
                    Used only when an FSA row is missing and your schedule allows distance fallback.
                    Base includes the first {card.included_km} km.
                  </p>
                  <VehicleTable card={card} />
                </details>
              ) : null}
            </>
          ) : (
            <>
              <p>
                Base fare includes the first {card.included_km} km. Extra kilometres and extra stops
                are added from the table below.
              </p>
              <VehicleTable card={card} />
              <dl className="grid gap-2 sm:grid-cols-2">
                <div className="flex justify-between gap-4">
                  <dt className="text-muted">Downtown surcharge</dt>
                  <dd>
                    {card.surcharges.downtown
                      ? formatCents(card.surcharges.downtown_cents ?? 0)
                      : "Waived"}
                  </dd>
                </div>
                <div className="flex justify-between gap-4">
                  <dt className="text-muted">Upper zone surcharge</dt>
                  <dd>
                    {card.surcharges.upper_zone
                      ? formatCents(card.surcharges.upper_zone_cents ?? 0)
                      : "Waived"}
                  </dd>
                </div>
                <div className="flex justify-between gap-4">
                  <dt className="text-muted">Liftgate</dt>
                  <dd>{formatCents(card.liftgate_cents)}</dd>
                </div>
                <div className="flex justify-between gap-4">
                  <dt className="text-muted">Fuel</dt>
                  <dd>{card.fuel_surcharge_percent}%</dd>
                </div>
                {card.schedule ? (
                  <>
                    <div className="flex justify-between gap-4">
                      <dt className="text-muted">FSA miss</dt>
                      <dd>
                        {card.schedule.fsa_miss === "refuse" ? "Refuse quote" : "Distance fallback"}
                      </dd>
                    </div>
                    <div className="flex justify-between gap-4">
                      <dt className="text-muted">Origin pickup</dt>
                      <dd>
                        {card.schedule.origin_pickup_cents > 0
                          ? formatCents(card.schedule.origin_pickup_cents)
                          : "—"}
                      </dd>
                    </div>
                    <div className="flex justify-between gap-4 sm:col-span-2">
                      <dt className="text-muted">Route minimums</dt>
                      <dd>
                        {Object.keys(card.schedule.route_minimums_cents || {}).length
                          ? Object.entries(card.schedule.route_minimums_cents)
                              .map(([k, v]) => `${k} ${formatCents(v)}`)
                              .join(" · ")
                          : "—"}
                      </dd>
                    </div>
                  </>
                ) : null}
                <div className="flex justify-between gap-4">
                  <dt className="text-muted">HST</dt>
                  <dd>
                    {card.tax.hst_percent}%{card.tax.tax_included ? " (included)" : ""}
                  </dd>
                </div>
                <div className="flex justify-between gap-4">
                  <dt className="text-muted">Ontario FSA rows</dt>
                  <dd>
                    {card.fsa_rate_count} of yours · {card.platform_fsa_rate_count} platform
                  </dd>
                </div>
              </dl>
              {card.size_tiers.length > 0 && (
                <div>
                  <h3 className="font-medium text-primary">Size and weight</h3>
                  <ul className="mt-2 list-disc space-y-1 pl-5 text-muted">
                    {card.size_tiers.map((t, i) => (
                      <li key={i}>
                        {t.label || "Size rule"} — {formatCents(t.surcharge_cents)}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </>
          )}

          <p className="text-xs text-muted">
            Rates are set by PorterChain. You cannot edit them here.
          </p>
        </div>
      )}
    </section>
  );
}

function VehicleTable({ card }: { card: MerchantRateCard }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[32rem] text-left text-sm">
        <thead className="border-b border-primary/10 text-muted">
          <tr>
            <th className="py-2 font-medium">Vehicle</th>
            <th className="py-2 font-medium">Base</th>
            <th className="py-2 font-medium">Extra km</th>
            <th className="py-2 font-medium">Extra pickup</th>
            <th className="py-2 font-medium">Extra drop</th>
          </tr>
        </thead>
        <tbody>
          {card.vehicles.map((v) => (
            <tr key={v.id} className="border-b border-primary/5">
              <td className="py-2">{v.label}</td>
              <td className="py-2">{formatCents(v.base_cents)}</td>
              <td className="py-2">{formatCents(v.extra_km_cents)}</td>
              <td className="py-2">{formatCents(v.extra_pickup_cents)}</td>
              <td className="py-2">{formatCents(v.extra_drop_cents)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
