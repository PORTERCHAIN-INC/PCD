"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { formatCents } from "@porterchain/ui/utils";
import { Button, Input } from "@/components/crm/primitives";
import AdminPage from "@/components/layout/AdminPage";
import { FinanceNav } from "@/components/finance/FinanceShell";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { SendQuotePanel } from "@/components/pricing/QuoteAndAdjustments";
import LivePricingTable, { RetiredBanner } from "@/components/pricing/LivePricingTable";
import {
  dollarsToCents,
  guardrailTone,
  pctChange,
  rateCardApi,
  type OrgPricingBody,
  type PreviewRow,
  type RateCardLines,
  type StandardCard,
} from "@/lib/rate-card";

const TONE = {
  ok: "text-emerald-700",
  warn: "text-amber-700",
  blocked: "text-red-700 font-semibold",
} as const;

function PreviewTable({ rows }: { rows: PreviewRow[] }) {
  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="text-left text-muted-foreground">
          <th>Sample</th>
          <th>Standard</th>
          <th>This price</th>
          <th>Change</th>
          <th>HST</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((r) => {
          const pct = pctChange(r.standard_cents, r.custom_cents);
          return (
            <tr key={r.sample} className="border-t">
              <td className="py-1">{r.sample.replace(/_/g, " ")}</td>
              <td>{formatCents(r.standard_cents)}</td>
              <td>{formatCents(r.custom_cents)}</td>
              <td className={TONE[guardrailTone(pct)]}>
                {pct > 0 ? "+" : ""}
                {pct}%
              </td>
              <td>{formatCents(r.hst_cents)}</td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

function StandardEditor({ token }: { token: () => Promise<string | null> }) {
  const [card, setCard] = useState<StandardCard | null>(null);
  const [lines, setLines] = useState<RateCardLines | null>(null);
  const [preview, setPreview] = useState<PreviewRow[]>([]);
  const [diff, setDiff] = useState<Record<string, { from: unknown; to: unknown }>>({});
  const [reason, setReason] = useState("");
  const [msg, setMsg] = useState<string | null>(null);

  const load = useCallback(async () => {
    const t = await token();
    if (!t) return;
    const c = await rateCardApi.standard(t);
    setCard(c);
    setLines(structuredClone((c.draft ?? c.published)?.lines ?? null));
  }, [token]);
  useEffect(() => {
    void load();
  }, [load]);

  const runPreview = async (next: RateCardLines) => {
    const t = await token();
    if (!t) return;
    try {
      const p = await rateCardApi.preview(t, next);
      setPreview(p.rows);
      setDiff(p.diff);
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Preview failed");
    }
  };

  const setCents = (
    group: "bands" | "furniture_classes" | "add_ons",
    key: string,
    field: "z1_cents" | "cents",
    v: string
  ) => {
    if (!lines) return;
    const cents = dollarsToCents(v);
    if (cents == null) return;
    const next = structuredClone(lines);
    (next[group] as Record<string, Record<string, unknown>>)[key][field] = cents;
    setLines(next);
    void runPreview(next);
  };

  if (!card || !lines)
    return <p className="text-sm text-muted-foreground">Loading the Standard card…</p>;
  const edit = false; // 2026-10-31: the S/M/L/XL Standard card is retired (read only)
  const act = async (fn: (t: string) => Promise<unknown>, ok: string) => {
    const t = await token();
    if (!t) return;
    try {
      await fn(t);
      setMsg(ok);
      setReason("");
      await load();
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Failed");
    }
  };

  const row = (group: "bands" | "furniture_classes" | "add_ons", field: "z1_cents" | "cents") =>
    Object.entries(lines[group])
      .filter(([, v]) => !(v as { retired?: boolean }).retired) // 2-person and white-glove retired (doc 84 §8.1)
      .map(([k, v]) => (
        <label key={k} className="flex items-center justify-between gap-2 py-1 text-sm">
          <span>
            {k} · {(v as { label: string }).label}
          </span>
          <Input
            className="w-28"
            disabled={!edit}
            defaultValue={((v as Record<string, number>)[field] / 100).toFixed(2)}
            onBlur={(e) => setCents(group, k, field, e.target.value)}
          />
        </label>
      ));

  return (
    <section
      className="space-y-4 rounded-xl border p-4 opacity-80"
      aria-label="Retired Standard card (read only)"
    >
      <RetiredBanner what="Standard card S/M/L/XL, furniture classes and add-ons" />
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-lg font-semibold">
          Retired Standard card · live v{card.published?.version ?? "–"}
          {card.draft ? ` · draft v${card.draft.version}` : ""}
        </h2>
        <span className="text-xs text-muted-foreground">Read only</span>
      </div>
      <div className="grid gap-6 md:grid-cols-3">
        <div>
          <h3 className="font-medium">Size bands (Zone 1)</h3>
          {row("bands", "z1_cents")}
        </div>
        <div>
          <h3 className="font-medium">Furniture (Zone 1)</h3>
          {row("furniture_classes", "z1_cents")}
        </div>
        <div>
          <h3 className="font-medium">Add-ons</h3>
          {row("add_ons", "cents")}
        </div>
      </div>
      {preview.length ? <PreviewTable rows={preview} /> : null}
      {Object.keys(diff).length ? (
        <ul className="text-xs text-muted-foreground">
          {Object.entries(diff).map(([k, d]) => (
            <li key={k}>
              {k}: {String(d.from)} → {String(d.to)}
            </li>
          ))}
        </ul>
      ) : null}
      {edit ? (
        <div className="flex flex-wrap items-center gap-2">
          <Button onClick={() => act((t) => rateCardApi.saveDraft(t, lines), "Draft saved")}>
            Save draft
          </Button>
          <Input
            className="w-72"
            placeholder="Reason (required to publish or roll back)"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
          />
          <Button
            disabled={!card.draft || reason.length < 3}
            onClick={() => act((t) => rateCardApi.publish(t, reason), "Published")}
          >
            Publish
          </Button>
        </div>
      ) : null}
      <div>
        <h3 className="font-medium">Versions</h3>
        <ul className="text-sm">
          {card.versions.map((v) => (
            <li key={v.id} className="flex items-center gap-3 py-0.5">
              <span>
                v{v.version} · {v.status}
                {v.notes ? ` · ${v.notes}` : ""}
              </span>
              {edit && v.status === "retired" ? (
                <Button
                  disabled={reason.length < 3}
                  onClick={() =>
                    act(
                      (t) => rateCardApi.rollback(t, v.version, reason),
                      `Rolled back to v${v.version}`
                    )
                  }
                >
                  Roll back
                </Button>
              ) : null}
            </li>
          ))}
        </ul>
      </div>
      {msg ? <p className="text-sm">{msg}</p> : null}
    </section>
  );
}

export function OrgCustom({
  token,
  fixedOrgId,
}: {
  token: () => Promise<string | null>;
  fixedOrgId?: string;
}) {
  const [orgId, setOrgId] = useState(fixedOrgId ?? "");
  const [body, setBody] = useState<OrgPricingBody>({ mode: "standard" });
  const [rows, setRows] = useState<PreviewRow[]>([]);
  const [msg, setMsg] = useState<string | null>(null);

  const call = async <T,>(fn: (t: string) => Promise<T>): Promise<T | null> => {
    const t = await token();
    if (!t) return null;
    try {
      return await fn(t);
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Failed");
      return null;
    }
  };
  const load = async () => {
    const o = await call((t) => rateCardApi.org(t, orgId.trim()));
    if (!o) return;
    setBody({
      mode: o.mode,
      preset_pct: o.preset_pct,
      preset_per_stop_cents: o.preset_per_stop_cents,
      flat_parcel_cents: o.flat_parcel_cents ?? null,
      band_overrides: o.band_overrides,
      contract_document_id: o.contract_document_id,
    });
    setRows(o.preview ?? []);
  };
  useEffect(() => {
    if (fixedOrgId) void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fixedOrgId]);
  const update = async (next: OrgPricingBody) => {
    setBody(next);
    setMsg(null);
    const p = await call((t) => rateCardApi.previewOrg(t, orgId.trim(), next));
    if (p) setRows(p.rows);
  };

  return (
    <section className="space-y-3 rounded-xl border p-4">
      <h2 className="text-lg font-semibold">
        Pricing:{" "}
        {body.mode === "custom" ? "Custom merchant price" : "PorterChain Standard (default)"}
      </h2>
      <p className="text-xs text-muted-foreground">
        Standard = $6 / $9 parcels + handling, hourly vehicles. Custom sets a flat price per parcel
        (any size), or applies a % and/or a per-stop $ change to those prices, and overrides them
        for this merchant. Before HST.
      </p>
      <div className={fixedOrgId ? "hidden" : "flex flex-wrap gap-2"}>
        <Input
          className="w-72"
          placeholder="Organisation or merchant id"
          value={orgId}
          onChange={(e) => setOrgId(e.target.value)}
        />
        <Button disabled={!orgId.trim()} onClick={() => void load()}>
          Load
        </Button>
      </div>
      <div className="flex flex-wrap items-center gap-4 text-sm">
        {(["standard", "custom"] as const).map((m) => (
          <label key={m} className="flex items-center gap-1">
            <input
              type="radio"
              checked={body.mode === m}
              onChange={() => void update({ ...body, mode: m })}
            />{" "}
            {m === "standard" ? "Standard" : "Custom"}
          </label>
        ))}
        {body.mode === "custom" ? (
          <>
            <label className="flex items-center gap-1">
              Flat price per parcel $ (any size)
              <Input
                key={`flat-${orgId}-${body.flat_parcel_cents ?? ""}`}
                aria-label="Flat price per parcel"
                className="w-20"
                inputMode="decimal"
                defaultValue={
                  body.flat_parcel_cents != null ? (body.flat_parcel_cents / 100).toFixed(2) : ""
                }
                onBlur={(e) =>
                  void update({
                    ...body,
                    flat_parcel_cents: e.target.value ? dollarsToCents(e.target.value) : null,
                  })
                }
              />
            </label>
            <label className="flex items-center gap-1">
              Across the board %
              <Input
                className="w-20"
                type="number"
                value={body.preset_pct ?? ""}
                onChange={(e) =>
                  void update({
                    ...body,
                    preset_pct: e.target.value === "" ? null : Number(e.target.value),
                  })
                }
              />
            </label>
            <label className="flex items-center gap-1">
              Per stop $
              <Input
                key={`stop-${orgId}-${body.preset_per_stop_cents ?? ""}`}
                className="w-20"
                defaultValue={
                  body.preset_per_stop_cents != null
                    ? (body.preset_per_stop_cents / 100).toFixed(2)
                    : ""
                }
                onBlur={(e) =>
                  void update({
                    ...body,
                    preset_per_stop_cents: e.target.value ? dollarsToCents(e.target.value) : null,
                  })
                }
              />
            </label>
            <label className="flex items-center gap-1">
              Contract doc
              <Input
                className="w-40"
                value={body.contract_document_id ?? ""}
                onChange={(e) => setBody({ ...body, contract_document_id: e.target.value || null })}
              />
            </label>
          </>
        ) : null}
      </div>
      {rows.length ? <PreviewTable rows={rows} /> : null}
      <Button
        disabled={!orgId.trim()}
        onClick={async () => {
          const r = await call((t) => rateCardApi.saveOrg(t, orgId.trim(), body));
          if (r) setMsg("Saved");
        }}
      >
        Save organisation pricing
      </Button>
      {msg ? <p className="text-sm">{msg}</p> : null}
    </section>
  );
}

export default function RateCardClient() {
  const { getApiToken } = useAdminAuth();
  const token = useCallback(async () => (await getApiToken()) ?? null, [getApiToken]);
  return (
    <AdminPage
      title="Rate card"
      description="Live pricing: $6 / $9 parcels + handling, hourly vehicles for merchants, or a custom merchant price."
    >
      <FinanceNav />
      <p className="text-sm">
        <Link className="underline" href="/pricing">
          ← Quote simulator
        </Link>
      </p>
      <LivePricingTable />
      <OrgCustom token={token} />
      <StandardEditor token={token} />
    </AdminPage>
  );
}

/** Organisation profile → Money → Pricing (doc 75 §4). */
export function OrgPricingPanel({ orgId }: { orgId: string }) {
  const { getApiToken } = useAdminAuth();
  const token = useCallback(async () => (await getApiToken()) ?? null, [getApiToken]);
  return (
    <div className="space-y-4">
      <OrgCustom token={token} fixedOrgId={orgId} />
      <SendQuotePanel orgId={orgId} />
    </div>
  );
}
