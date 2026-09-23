"use client";

import { money } from "@/lib/crmFormat";
import { pricingModelLabel, type MerchantRateCard } from "@/lib/merchants";

export default function RateCardPreview({ card }: { card: MerchantRateCard }) {
  return (
    <div className="space-y-4 text-sm">
      <p>
        <span className="text-muted">How we price: </span>
        {pricingModelLabel(card.pricing_model)}
      </p>
      <p className="text-muted">{card.what_wins}</p>
      <p>
        Base fare includes the first {card.included_km} km. Extra kilometres and extra stops are
        added from the table below.
      </p>
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
                <td className="py-2">{money(v.base_cents)}</td>
                <td className="py-2">{money(v.extra_km_cents)}</td>
                <td className="py-2">{money(v.extra_pickup_cents)}</td>
                <td className="py-2">{money(v.extra_drop_cents)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <dl className="grid gap-2 sm:grid-cols-2">
        <div className="flex justify-between gap-4">
          <dt className="text-muted">Downtown surcharge</dt>
          <dd>
            {card.surcharges.downtown ? money(card.surcharges.downtown_cents ?? 0) : "Waived"}
          </dd>
        </div>
        <div className="flex justify-between gap-4">
          <dt className="text-muted">Upper zone surcharge</dt>
          <dd>
            {card.surcharges.upper_zone ? money(card.surcharges.upper_zone_cents ?? 0) : "Waived"}
          </dd>
        </div>
        <div className="flex justify-between gap-4">
          <dt className="text-muted">Liftgate</dt>
          <dd>{money(card.liftgate_cents)}</dd>
        </div>
        <div className="flex justify-between gap-4">
          <dt className="text-muted">Fuel</dt>
          <dd>{card.fuel_surcharge_percent}%</dd>
        </div>
        {card.schedule ? (
          <>
            <div className="flex justify-between gap-4">
              <dt className="text-muted">FSA miss</dt>
              <dd>{card.schedule.fsa_miss === "refuse" ? "Refuse quote" : "Distance fallback"}</dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-muted">Origin pickup</dt>
              <dd>
                {card.schedule.origin_pickup_cents > 0
                  ? money(card.schedule.origin_pickup_cents)
                  : "—"}
              </dd>
            </div>
            <div className="flex justify-between gap-4 sm:col-span-2">
              <dt className="text-muted">Route minimums</dt>
              <dd>
                {Object.keys(card.schedule.route_minimums_cents || {}).length
                  ? Object.entries(card.schedule.route_minimums_cents)
                      .map(([k, v]) => `${k} ${money(v)}`)
                      .join(" · ")
                  : "—"}
              </dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-muted">Size match</dt>
              <dd>{card.schedule.size_match === "any" ? "Weight or footprint" : "All limits"}</dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-muted">Compact banding</dt>
              <dd>{card.schedule.compact?.enabled ? "On" : "Off"}</dd>
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
          <dt className="text-muted">Weight over {card.weight.threshold_kg} kg</dt>
          <dd>{money(card.weight.cents_per_kg)} / kg</dd>
        </div>
        <div className="flex justify-between gap-4">
          <dt className="text-muted">Ontario FSA rows</dt>
          <dd>
            {card.fsa_rate_count} of this merchant · {card.platform_fsa_rate_count} platform
          </dd>
        </div>
      </dl>
      {card.size_tiers.length > 0 && (
        <div>
          <h3 className="font-medium text-primary">Size and weight</h3>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-muted">
            {card.size_tiers.map((t, i) => (
              <li key={i}>
                {t.label || "Size rule"} — {money(t.surcharge_cents)}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
