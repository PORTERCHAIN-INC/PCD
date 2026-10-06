"use client";

import { useCallback, useEffect, useState } from "react";
import { Lock, RefreshCw } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { PageSkeleton } from "@porterchain/ui/loading";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { SECTION_DESCRIPTIONS } from "@/lib/settings-metadata";
import { settingsApi, type LeadIngestSettings } from "@/lib/settings";
import { withStaffStepUp } from "@/lib/staff-step-up";
import { BindingBadge, SettingsCard, SettingsPageHeader } from "../ui/SettingsPrimitives";
import { LeadSuppressionCard } from "./LeadSuppressionCard";
import { LeadRopaCard } from "./LeadRopaCard";

const SECRET_META: Array<{ key: string; label: string; hint: string; canGenerate?: boolean }> = [
  {
    key: "PUBLIC_INGEST_API_KEY",
    label: "Public ingest API key",
    hint: "Website → API inquiries (X-Ingest-Key)",
    canGenerate: true,
  },
  {
    key: "GOOGLE_LEAD_WEBHOOK_SECRET",
    label: "Google lead webhook secret",
    hint: "Header X-Lead-Webhook-Secret for Google Ads / GBP",
    canGenerate: true,
  },
  {
    key: "SOCIAL_LEAD_WEBHOOK_SECRET",
    label: "Social lead webhook secret",
    hint: "LinkedIn / X / YouTube shared header secret",
    canGenerate: true,
  },
  {
    key: "META_APP_SECRET",
    label: "Meta app secret",
    hint: "HMAC for Meta Lead Ads / WhatsApp / Instagram webhooks",
  },
  {
    key: "META_WEBHOOK_VERIFY_TOKEN",
    label: "Meta webhook verify token",
    hint: "Hub challenge token for Meta callback",
    canGenerate: true,
  },
  {
    key: "META_CAPI_ACCESS_TOKEN",
    label: "Meta CAPI access token",
    hint: "CRM offline conversions on lead convert",
  },
  {
    key: "LINKEDIN_CAPI_TOKEN",
    label: "LinkedIn CAPI token",
    hint: "LinkedIn Conversions API bearer token",
  },
];

function StatusDot({ ok }: { ok: boolean }) {
  return (
    <span
      className={`inline-block h-2 w-2 rounded-full ${ok ? "bg-emerald-500" : "bg-slate-300"}`}
      title={ok ? "Configured" : "Not set"}
    />
  );
}

export default function LeadIngestPanel() {
  const { getApiToken, isLoaded, isSignedIn } = useAdminAuth();
  const [data, setData] = useState<LeadIngestSettings | null>(null);
  const [error, setError] = useState("");
  const [okMsg, setOkMsg] = useState("");
  const [busy, setBusy] = useState(false);
  const [secretDrafts, setSecretDrafts] = useState<Record<string, string>>({});
  const [visible, setVisible] = useState({
    META_PIXEL_ID: "",
    LINKEDIN_CONVERSION_URN: "",
    LEAD_TERRITORY_MAP_JSON: "",
    LEAD_ROUND_ROBIN_JSON: "",
    LEAD_SLA_MINUTES_JSON: "",
    REFERRAL_CREDIT_CENTS: 25000,
  });

  const query = useQuery({
    queryKey: ["admin", "lead-ingest"],
    enabled: isLoaded && isSignedIn,
    queryFn: async () => settingsApi.leadIngest(await getApiToken()),
  });

  useEffect(() => {
    if (!query.data) return;
    const res = query.data;
    setData(res);
    setVisible({
      META_PIXEL_ID: res.visible.META_PIXEL_ID ?? "",
      LINKEDIN_CONVERSION_URN: res.visible.LINKEDIN_CONVERSION_URN ?? "",
      LEAD_TERRITORY_MAP_JSON: res.visible.LEAD_TERRITORY_MAP_JSON ?? "",
      LEAD_ROUND_ROBIN_JSON: res.visible.LEAD_ROUND_ROBIN_JSON ?? "",
      LEAD_SLA_MINUTES_JSON: res.visible.LEAD_SLA_MINUTES_JSON ?? "",
      REFERRAL_CREDIT_CENTS: res.visible.REFERRAL_CREDIT_CENTS ?? 25000,
    });
    setSecretDrafts({});
  }, [query.data]);

  useEffect(() => {
    if (query.error)
      setError(query.error instanceof Error ? query.error.message : "Failed to load");
  }, [query.error]);

  const load = useCallback(async () => {
    setError("");
    await query.refetch();
  }, [query.refetch]);

  async function save(extra?: { generate?: string[] }) {
    setBusy(true);
    setError("");
    setOkMsg("");
    try {
      const token = await getApiToken();
      const secrets: Record<string, string> = {};
      for (const [k, v] of Object.entries(secretDrafts)) {
        if (v.trim()) secrets[k] = v.trim();
      }
      const res = await withStaffStepUp(token, () =>
        settingsApi.updateLeadIngest(token, {
          secrets,
          visible,
          generate: extra?.generate,
        })
      );
      setData(res);
      setVisible({
        META_PIXEL_ID: res.visible.META_PIXEL_ID ?? "",
        LINKEDIN_CONVERSION_URN: res.visible.LINKEDIN_CONVERSION_URN ?? "",
        LEAD_TERRITORY_MAP_JSON: res.visible.LEAD_TERRITORY_MAP_JSON ?? "",
        LEAD_ROUND_ROBIN_JSON: res.visible.LEAD_ROUND_ROBIN_JSON ?? "",
        LEAD_SLA_MINUTES_JSON: res.visible.LEAD_SLA_MINUTES_JSON ?? "",
        REFERRAL_CREDIT_CENTS: res.visible.REFERRAL_CREDIT_CENTS ?? 25000,
      });
      setSecretDrafts({});
      const written = res.save?.written?.length
        ? `Saved to Doppler: ${res.save.written.join(", ")}`
        : "Saved";
      setOkMsg(written);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed");
    } finally {
      setBusy(false);
    }
  }

  if (!data && !error) {
    return <PageSkeleton rows={4} />;
  }

  return (
    <div className="space-y-6">
      <SettingsPageHeader
        title="Lead Ingest"
        description={SECTION_DESCRIPTIONS.lead_ingest}
        actions={<BindingBadge effect="env" />}
      />

      <div className="inline-flex items-center gap-2 rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-600">
        <Lock className="h-3.5 w-3.5" />
        Secret values never displayed — leave blank to keep current
      </div>

      <SettingsCard title="Doppler">
        <p className="text-sm text-muted">
          Project <code className="text-xs">{data?.doppler.project}</code> / config{" "}
          <code className="text-xs">{data?.doppler.config}</code>
          {" · "}
          {data?.doppler.configured ? (
            <span className="text-emerald-700">write enabled</span>
          ) : (
            <span className="text-amber-700">DOPPLER_TOKEN missing on API — saves will fail</span>
          )}
        </p>
        <p className="mt-2 text-xs text-muted">{data?.note}</p>
      </SettingsCard>

      {error ? <p className="text-sm text-red-600">{error}</p> : null}
      {okMsg ? <p className="text-sm text-emerald-700">{okMsg}</p> : null}

      <SettingsCard title="Webhook & CAPI secrets">
        <ul className="space-y-4">
          {SECRET_META.map((row) => {
            const st = data?.secrets[row.key];
            return (
              <li key={row.key} className="grid gap-2 sm:grid-cols-[1fr_auto] sm:items-end">
                <div>
                  <div className="flex items-center gap-2 text-sm font-medium text-primary">
                    <StatusDot ok={Boolean(st?.configured)} />
                    {row.label}
                  </div>
                  <p className="mt-0.5 text-xs text-muted">{row.hint}</p>
                  <input
                    type="password"
                    autoComplete="off"
                    placeholder={
                      st?.configured ? "•••••••• (unchanged if blank)" : "Paste new value"
                    }
                    className="mt-2 w-full rounded-lg border border-primary/15 px-3 py-2 text-sm"
                    value={secretDrafts[row.key] ?? ""}
                    onChange={(e) => setSecretDrafts((d) => ({ ...d, [row.key]: e.target.value }))}
                  />
                </div>
                {row.canGenerate ? (
                  <button
                    type="button"
                    disabled={busy}
                    className="rounded-lg border border-primary/15 px-3 py-2 text-xs font-medium text-primary hover:bg-slate-50 disabled:opacity-50"
                    onClick={() => void save({ generate: [row.key] })}
                  >
                    Generate & save
                  </button>
                ) : null}
              </li>
            );
          })}
        </ul>
      </SettingsCard>

      <SettingsCard title="Visible config">
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="block text-sm">
            <span className="text-muted">Meta pixel ID</span>
            <input
              className="mt-1 w-full rounded-lg border border-primary/15 px-3 py-2"
              value={visible.META_PIXEL_ID}
              onChange={(e) => setVisible((v) => ({ ...v, META_PIXEL_ID: e.target.value }))}
            />
          </label>
          <label className="block text-sm">
            <span className="text-muted">LinkedIn conversion URN</span>
            <input
              className="mt-1 w-full rounded-lg border border-primary/15 px-3 py-2"
              value={visible.LINKEDIN_CONVERSION_URN}
              onChange={(e) =>
                setVisible((v) => ({ ...v, LINKEDIN_CONVERSION_URN: e.target.value }))
              }
              placeholder="urn:lla:llaPartnerConversion:…"
            />
          </label>
          <label className="block text-sm sm:col-span-2">
            <span className="text-muted">Territory map JSON</span>
            <textarea
              className="mt-1 w-full rounded-lg border border-primary/15 px-3 py-2 font-mono text-xs"
              rows={3}
              value={visible.LEAD_TERRITORY_MAP_JSON}
              onChange={(e) =>
                setVisible((v) => ({ ...v, LEAD_TERRITORY_MAP_JSON: e.target.value }))
              }
              placeholder='{"ON":"<admin_user_id>","DEFAULT":"<admin_user_id>"}'
            />
          </label>
          <label className="block text-sm sm:col-span-2">
            <span className="text-muted">Round-robin assignee pool JSON</span>
            <textarea
              className="mt-1 w-full rounded-lg border border-primary/15 px-3 py-2 font-mono text-xs"
              rows={2}
              value={visible.LEAD_ROUND_ROBIN_JSON}
              onChange={(e) => setVisible((v) => ({ ...v, LEAD_ROUND_ROBIN_JSON: e.target.value }))}
              placeholder='["<admin_user_id>","<admin_user_id>"]'
            />
          </label>
          <label className="block text-sm sm:col-span-2">
            <span className="text-muted">SLA minutes by channel JSON</span>
            <textarea
              className="mt-1 w-full rounded-lg border border-primary/15 px-3 py-2 font-mono text-xs"
              rows={2}
              value={visible.LEAD_SLA_MINUTES_JSON}
              onChange={(e) => setVisible((v) => ({ ...v, LEAD_SLA_MINUTES_JSON: e.target.value }))}
              placeholder='{"whatsapp":15,"phone_call":30,"default":60}'
            />
          </label>
          <label className="block text-sm">
            <span className="text-muted">Referral credit (cents)</span>
            <input
              type="number"
              className="mt-1 w-full rounded-lg border border-primary/15 px-3 py-2"
              value={visible.REFERRAL_CREDIT_CENTS}
              onChange={(e) =>
                setVisible((v) => ({
                  ...v,
                  REFERRAL_CREDIT_CENTS: Number(e.target.value) || 0,
                }))
              }
            />
          </label>
        </div>
      </SettingsCard>

      <LeadSuppressionCard />
      <LeadRopaCard />

      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          disabled={busy}
          className="rounded-lg bg-secondary px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
          onClick={() => void save()}
          aria-label="Save lead ingest settings to Doppler"
        >
          {busy ? "Saving…" : "Save to Doppler"}
        </button>
        <button
          type="button"
          disabled={busy}
          className="inline-flex items-center gap-1.5 rounded-lg border border-primary/15 px-4 py-2 text-sm disabled:opacity-50"
          onClick={() => void load()}
        >
          <RefreshCw className="h-3.5 w-3.5" /> Refresh
        </button>
      </div>
    </div>
  );
}
