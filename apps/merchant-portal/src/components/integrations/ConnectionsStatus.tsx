"use client";

/**
 * Connections at a glance: one status line, one row per integration
 * (green / amber / red + plain reason), one Fix button each, details collapsed.
 * Same health object staff see in admin, so the two never disagree.
 */

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";
import { useMerchantAuth } from "@/hooks/useMerchantAuth";
import { integrationsApi } from "@/lib/integrations";
import {
  hookRow,
  keyRow,
  shopRow,
  summary,
  type Light,
  type MerchantFix,
  type Row,
} from "@/lib/connectionStatus";

const DOT: Record<Light, string> = {
  red: "bg-red-600",
  amber: "bg-amber-500",
  green: "bg-emerald-600",
  off: "bg-slate-300",
};
const WORD: Record<Light, string> = {
  red: "Needs attention",
  amber: "Watch",
  green: "Healthy",
  off: "Off",
};
const GROUP: Record<Row["group"], string> = {
  shopify: "Shopify",
  keys: "API keys",
  webhooks: "Order updates to your system",
};

export default function ConnectionsStatus({ title = "Connections" }: { title?: string }) {
  const { getApiToken, orgId, isSignedIn } = useMerchantAuth();
  const [toast, setToast] = useState<{ text: string; bad?: boolean } | null>(null);
  const [busy, setBusy] = useState(false);

  const q = useQuery({
    queryKey: ["merchant-connections-status", orgId],
    enabled: Boolean(isSignedIn && orgId),
    queryFn: async () => {
      const t = await getApiToken();
      const [shopify, keys, hooks, logs] = await Promise.all([
        integrationsApi.shopify(t, orgId ?? undefined),
        integrationsApi.listKeys(t, orgId ?? undefined).catch(() => []),
        integrationsApi.listWebhooks(t, orgId ?? undefined).catch(() => []),
        integrationsApi.webhookLogs(t, orgId ?? undefined).catch(() => []),
      ]);
      return { shopify, keys, hooks, logs };
    },
  });

  async function fix(f: MerchantFix) {
    if (f.kind === "link") return;
    setBusy(true);
    setToast(null);
    try {
      const t = await getApiToken();
      if (f.kind === "reconnect") {
        const res = await integrationsApi.shopifyInstallUrl(t, f.shop, orgId ?? undefined);
        window.location.assign(res.url);
        return;
      }
      const out = await integrationsApi.shopifyGoLive(t, { shop_id: f.shopId }, orgId ?? undefined);
      setToast(
        out.go_live?.ready
          ? { text: "Setup finished — checkout rates are live" }
          : { text: "Still not live — see the reason above", bad: true }
      );
      await q.refetch();
    } catch (e) {
      setToast({ text: e instanceof Error ? e.message : "That didn't work", bad: true });
    } finally {
      setBusy(false);
    }
  }

  if (q.isLoading) {
    return (
      <section
        aria-busy="true"
        aria-label="Checking connections"
        className="rounded-3xl border border-primary/10 bg-white p-6"
      >
        <div className="h-3 w-24 animate-pulse rounded bg-slate-200" />
        <div className="mt-3 h-8 w-56 animate-pulse rounded bg-slate-200" />
        <div className="mt-6 space-y-3">
          {[0, 1, 2].map((i) => (
            <div key={i} className="h-10 animate-pulse rounded-xl bg-slate-100" />
          ))}
        </div>
      </section>
    );
  }
  if (q.error || !q.data) {
    return (
      <section className="rounded-3xl border border-primary/10 bg-white p-6">
        <p className="font-bold text-primary">Couldn&apos;t check your connections</p>
        <button
          type="button"
          onClick={() => void q.refetch()}
          className="mt-3 min-h-11 rounded-full border border-primary/15 px-4 text-sm font-semibold text-primary"
        >
          Try again
        </button>
      </section>
    );
  }

  const rows: Row[] = [
    ...q.data.shopify.shops.map(shopRow),
    ...q.data.keys.map((k) => keyRow(k)),
    ...q.data.hooks.map((w) => hookRow(w, q.data.logs)),
  ];
  const sum = summary(rows);
  const firstFix = rows.find((r) => r.fix && r.light === "red") ?? rows.find((r) => r.fix);

  return (
    <section className="rounded-3xl border border-primary/10 bg-white">
      <div className="p-5 sm:p-6">
        <p className="text-[11px] font-semibold tracking-[0.18em] text-secondary uppercase">
          {title}
        </p>
        <p className="mt-1 flex items-center gap-2.5 text-2xl font-extrabold tracking-tight text-primary sm:text-3xl">
          <span className={`h-3 w-3 rounded-full ${DOT[sum.light]}`} aria-hidden />
          {sum.line}
        </p>
        {toast ? (
          <p
            role="status"
            className={`mt-3 text-sm font-semibold ${toast.bad ? "text-red-700" : "text-emerald-700"}`}
          >
            {toast.text}
          </p>
        ) : null}
      </div>
      {rows.length === 0 ? (
        <div className="border-t border-primary/10 px-5 py-8 text-center sm:px-6">
          <p className="font-bold text-primary">Connect your Shopify store or create an API key</p>
          <p className="mt-1 text-sm text-slate-600">Orders then flow in on their own.</p>
          <Link
            href="/shopify"
            className="mt-4 inline-flex min-h-11 items-center rounded-full bg-secondary px-5 text-sm font-bold text-white"
          >
            Connect Shopify
          </Link>
        </div>
      ) : (
        (["shopify", "keys", "webhooks"] as const)
          .filter((g) => rows.some((r) => r.group === g))
          .map((g) => (
            <div key={g} className="border-t border-primary/10 px-5 sm:px-6">
              <h3 className="pt-4 text-[11px] font-semibold tracking-[0.14em] text-slate-600 uppercase">
                {GROUP[g]}
              </h3>
              <ul className="divide-y divide-primary/5">
                {rows
                  .filter((r) => r.group === g)
                  .map((r) => (
                    <StatusRow
                      key={r.id}
                      row={r}
                      primary={r === firstFix}
                      busy={busy}
                      onFix={fix}
                    />
                  ))}
              </ul>
            </div>
          ))
      )}
    </section>
  );
}

function StatusRow({
  row,
  primary,
  busy,
  onFix,
}: {
  row: Row;
  primary: boolean;
  busy: boolean;
  onFix: (f: MerchantFix) => void;
}) {
  const [open, setOpen] = useState(false);
  const cls = primary
    ? "bg-secondary text-white hover:opacity-90"
    : "border border-primary/15 text-primary hover:bg-slate-50";
  const f = row.fix;
  return (
    <li className="py-4">
      <div className="flex flex-wrap items-center gap-3">
        <span className={`h-2.5 w-2.5 shrink-0 rounded-full ${DOT[row.light]}`} aria-hidden />
        <div className="min-w-0 flex-1 basis-44">
          <p className="truncate text-[15px] font-bold text-primary">{row.name}</p>
          <p
            className={`text-sm ${row.light === "red" ? "text-red-700" : row.light === "amber" ? "text-amber-800" : "text-slate-600"}`}
          >
            <span className="sr-only">{WORD[row.light]}: </span>
            {row.reason}
            {row.more.length ? (
              <span className="text-slate-600"> · +{row.more.length} more</span>
            ) : null}
          </p>
        </div>
        {f ? (
          f.kind === "link" ? (
            <a
              href={f.href}
              className={`inline-flex min-h-11 items-center rounded-full px-4 text-sm font-bold ${cls}`}
            >
              {f.label}
            </a>
          ) : (
            <button
              type="button"
              disabled={busy}
              onClick={() => onFix(f)}
              className={`inline-flex min-h-11 items-center rounded-full px-4 text-sm font-bold disabled:opacity-50 ${cls}`}
            >
              {f.label}
            </button>
          )
        ) : null}
        {row.more.length ? (
          <button
            type="button"
            aria-expanded={open}
            onClick={() => setOpen((v) => !v)}
            className="inline-flex min-h-11 items-center rounded-full px-3 text-sm font-semibold text-slate-600 hover:text-primary"
          >
            Details
          </button>
        ) : null}
      </div>
      {open ? (
        <ul className="mt-3 ml-5 space-y-1 rounded-2xl bg-slate-50 px-4 py-3 text-sm text-red-700">
          {row.more.map((m) => (
            <li key={m}>{m}</li>
          ))}
        </ul>
      ) : null}
    </li>
  );
}
