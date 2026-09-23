"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { RotateCcw, Save } from "lucide-react";
import { Button, SectionCard, Spinner } from "@/components/crm/primitives";
import MerchantPricingFields from "@/components/merchants/MerchantPricingFields";
import MerchantGtaMatrixFields from "@/components/merchants/MerchantGtaMatrixFields";
import RateCardPreview from "@/components/merchants/RateCardPreview";
import FsaRatesCard from "@/components/settings/panels/FsaRatesCard";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { useApiData } from "@/hooks/useApiData";
import { merchants, type MerchantPricing, type MerchantPricingDetail } from "@/lib/merchants";
import { settingsApi, type VehicleClassConfig } from "@/lib/settings";

function stripDetail(d: MerchantPricingDetail): MerchantPricing {
  return {
    pricing_model: d.pricing_model,
    surcharges: { ...d.surcharges },
    size_tiers: d.size_tiers.map((t) => ({ ...t })),
    gta_rate: d.gta_rate ?? null,
    schedule: d.schedule
      ? {
          ...d.schedule,
          route_minimums_cents: { ...(d.schedule.route_minimums_cents || {}) },
          origin_pickup_vehicle_classes: [...(d.schedule.origin_pickup_vehicle_classes || [])],
          compact: {
            ...d.schedule.compact,
            vehicle_classes: [...(d.schedule.compact?.vehicle_classes || [])],
            max_packed_inches: [...(d.schedule.compact?.max_packed_inches || [10, 10])],
            stop_rates_cents: (d.schedule.compact?.stop_rates_cents || []).map((b) => ({ ...b })),
          },
        }
      : null,
  };
}

export default function MerchantPricingPanel({ merchantId }: { merchantId: string }) {
  const { getApiToken } = useAdminAuth();
  const { data, loading, error, refetch } = useApiData<MerchantPricingDetail>(
    (token) => merchants.pricing(token, merchantId),
    [merchantId],
    { key: `merchant-pricing-${merchantId}` }
  );
  const { data: settings } = useApiData((token) => settingsApi.config(token), [], {
    key: "merchant-pricing-settings",
    staleTime: 300_000,
  });

  const catalog = useMemo(() => {
    const raw = settings?.config?.vehicles;
    if (!Array.isArray(raw)) return [] as VehicleClassConfig[];
    return raw.filter(
      (v): v is VehicleClassConfig => typeof v === "object" && v !== null && "id" in v
    );
  }, [settings]);

  const [draft, setDraft] = useState<MerchantPricing | null>(null);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    if (data) setDraft(stripDetail(data));
  }, [data]);

  if (loading || !draft) return <Spinner label="Loading pricing…" />;
  if (error) return <p className="py-8 text-center text-sm text-red-700">{error}</p>;

  const dirty = data ? JSON.stringify(draft) !== JSON.stringify(stripDetail(data)) : false;
  const fsaSelected = draft.pricing_model === "fsa";
  const distanceSelected = draft.pricing_model === "distance";
  const noOwnRates = draft.pricing_model === "fsa" && data !== null && data.fsa_rate_count === 0;
  const vehicleIds = catalog.map((v) => v.id);
  const vehicleLabels = Object.fromEntries(catalog.map((v) => [v.id, v.label]));

  async function save() {
    if (!draft) return;
    setSaving(true);
    try {
      await merchants.savePricing(await getApiToken(), merchantId, draft);
      await refetch();
      setMessage("Saved — the next quote for this merchant uses these settings.");
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm text-muted">
          Overrides the platform defaults for this merchant only. Merchant-scoped contract tariffs,
          when present, still take precedence over FSA and Distance here.
        </p>
        <div className="flex w-full flex-wrap items-center gap-2 sm:w-auto">
          <Button
            variant="outline"
            disabled={!dirty || saving}
            onClick={() => data && setDraft(stripDetail(data))}
          >
            <RotateCcw className="h-4 w-4" /> Reset
          </Button>
          <Button variant="primary" disabled={!dirty || saving} onClick={() => void save()}>
            <Save className="h-4 w-4" /> {saving ? "Saving…" : "Save"}
          </Button>
        </div>
      </div>

      {message && <p className="text-sm text-secondary">{message}</p>}

      {data?.card && (
        <SectionCard title="What this merchant sees">
          <div className="p-5">
            <RateCardPreview card={data.card} />
            <p className="mt-4 text-xs text-muted">
              Same card as merchant Contract and the partner rate-card GET. Edit the controls below,
              or change platform defaults in Settings → Pricing.
            </p>
          </div>
        </SectionCard>
      )}

      <SectionCard>
        <div className="p-5">
          <MerchantPricingFields
            value={draft}
            onChange={(next) => {
              setDraft(next);
              setMessage(null);
            }}
            fsaHint={
              <p
                className={`mt-3 rounded-xl px-3 py-2 text-sm ${
                  noOwnRates
                    ? "border border-amber-200 bg-amber-50 text-amber-900"
                    : "bg-gray-bg text-secondary"
                }`}
              >
                {noOwnRates
                  ? `No FSA rates are set for this merchant. It will fall back to ${
                      data && data.platform_fsa_rate_count > 0
                        ? `the ${data.platform_fsa_rate_count} platform-wide rate(s), then distance.`
                        : "distance pricing on every delivery."
                    }`
                  : `${data?.fsa_rate_count ?? 0} rate(s) set for this merchant, plus ${data?.platform_fsa_rate_count ?? 0} platform-wide.`}
              </p>
            }
          />
        </div>
      </SectionCard>

      {distanceSelected && (
        <SectionCard title={data?.has_custom_gta ? "Custom distance rates" : "Distance rates"}>
          <div className="p-5">
            <MerchantGtaMatrixFields
              value={draft.gta_rate}
              platform={data?.platform_gta_rate}
              vehicleIds={vehicleIds}
              labels={vehicleLabels}
              onChange={(gta_rate) => {
                setDraft({ ...draft, gta_rate });
                setMessage(null);
              }}
            />
          </div>
        </SectionCard>
      )}

      {fsaSelected && (
        <FsaRatesCard
          merchantId={merchantId}
          vehicleCatalog={catalog}
          embedded
          onChanged={() => void refetch()}
        />
      )}

      <p className="text-xs text-muted">
        Platform-wide FSA rates and the GTA matrix live in{" "}
        <Link href="/settings?section=pricing" className="font-medium text-secondary underline">
          Settings → Pricing
        </Link>
        .
      </p>
    </div>
  );
}
