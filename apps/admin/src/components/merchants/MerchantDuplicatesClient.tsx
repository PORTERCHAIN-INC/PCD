"use client";

import { useState } from "react";
import { useApiData } from "@/hooks/useApiData";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { Badge, SectionCard } from "@/components/crm/primitives";
import { merchantDuplicates, type DuplicateItem } from "@/lib/merchant-duplicates";

const REASON: Record<string, string> = {
  admin_issued_install_url: "Install link sent from this company",
  shop_domain: "Same Shopify store",
  business_number: "Same BN / HST number",
  email_domain: "Same company email domain",
  website_domain: "Same website",
  email_domain_is_name: "Email domain matches company name",
  phone: "Same phone",
  postal_code: "Same postal code",
};

function reasonLabel(r: string): string {
  return r.startsWith("name~") ? `Similar name (${r.slice(5)})` : (REASON[r] ?? r);
}

function Row({ item, onDone }: { item: DuplicateItem; onDone: () => void }) {
  const { getApiToken } = useAdminAuth();
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [undoId, setUndoId] = useState<string | null>(null);
  const moves = Object.entries(item.preview);

  async function run(fn: (t: string) => Promise<unknown>, after: (r: unknown) => void) {
    setBusy(true);
    setMsg(null);
    try {
      after(await fn(await getApiToken()));
    } catch (e) {
      setMsg(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-3 border-b border-slate-200 px-5 py-4 text-sm last:border-0">
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone={item.score >= 0.9 ? "red" : "amber"}>
          Match {Math.round(item.score * 100)}%
        </Badge>
        <span className="text-xs text-slate-500">via {item.source}</span>
      </div>
      <div className="grid gap-3 md:grid-cols-2">
        <div>
          <div className="text-xs uppercase text-slate-500">New record</div>
          <div className="font-medium">{item.company_name}</div>
          <div className="text-slate-600">{item.email}</div>
        </div>
        <div>
          <div className="text-xs uppercase text-slate-500">Existing company</div>
          <div className="font-medium">{item.match_company_name}</div>
          <div className="text-slate-600">{item.match_email}</div>
        </div>
      </div>
      <ul className="flex flex-wrap gap-2">
        {item.reasons.map((r) => (
          <li key={r}>
            <Badge tone="slate">{reasonLabel(r)}</Badge>
          </li>
        ))}
      </ul>
      <div className="text-slate-600">
        Merge moves:{" "}
        {moves.length
          ? moves.map(([t, n]) => `${n} ${t.replaceAll("_", " ")}`).join(", ")
          : "nothing"}
      </div>
      <div className="flex gap-2">
        {undoId ? (
          <button
            className="rounded border px-3 py-1"
            disabled={busy}
            onClick={() =>
              run(
                (t) => merchantDuplicates.undo(t, undoId),
                () => {
                  setUndoId(null);
                  onDone();
                }
              )
            }
          >
            Undo merge
          </button>
        ) : (
          <>
            <button
              className="rounded bg-slate-900 px-3 py-1 text-white"
              disabled={busy}
              onClick={() => {
                if (
                  !confirm(
                    `Merge "${item.company_name}" into "${item.match_company_name}"? You can undo this.`
                  )
                )
                  return;
                run(
                  (t) => merchantDuplicates.merge(t, item.merchant_id, item.match_merchant_id),
                  (r) => {
                    setUndoId((r as { merge_id: string }).merge_id);
                    setMsg("Merged.");
                  }
                );
              }}
            >
              Merge into existing
            </button>
            <button
              className="rounded border px-3 py-1"
              disabled={busy}
              onClick={() =>
                run((t) => merchantDuplicates.keepSeparate(t, item.merchant_id), onDone)
              }
            >
              Keep separate
            </button>
          </>
        )}
      </div>
      {msg ? <div className="text-xs text-slate-600">{msg}</div> : null}
    </div>
  );
}

export default function MerchantDuplicatesClient() {
  const { data, error, refetch } = useApiData((t) => merchantDuplicates.list(t), [], {
    key: "merchant-duplicates",
  });
  return (
    <div className="space-y-4 p-6">
      <h1 className="text-xl font-semibold">Possible duplicate companies</h1>
      <p className="text-sm text-slate-600">
        New signups and installs that look like an existing company. Nothing is joined
        automatically, and the person signing up is never shown the other account.
      </p>
      <SectionCard title={`Review queue (${data?.items.length ?? 0})`}>
        {error ? <div className="px-5 py-4 text-sm text-red-600">{String(error)}</div> : null}
        {data?.items.length === 0 ? (
          <div className="px-5 py-4 text-sm">No possible duplicates.</div>
        ) : null}
        {data?.items.map((i) => (
          <Row key={i.merchant_id} item={i} onDone={() => void refetch?.()} />
        ))}
      </SectionCard>
    </div>
  );
}
