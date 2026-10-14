"use client";

import { useEffect, useState } from "react";
import { useMerchantAuth } from "@/hooks/useMerchantAuth";
import {
  downloadContractDocument,
  listContractDocuments,
  type ContractDocument,
} from "@/lib/settings";
import { PRICING_EXAMPLE, PRICING_RULES } from "@/lib/pricingRules";

export default function HowWePriceClient() {
  const { getApiToken, orgId, isSignedIn } = useMerchantAuth();
  const [docs, setDocs] = useState<ContractDocument[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isSignedIn) return;
    let live = true;
    (async () => {
      try {
        const token = await getApiToken();
        const res = await listContractDocuments(token, orgId ?? undefined);
        if (live) setDocs(res.items);
      } catch (e) {
        if (live) setError(e instanceof Error ? e.message : "Could not load documents");
      }
    })();
    return () => {
      live = false;
    };
  }, [getApiToken, orgId, isSignedIn]);

  return (
    <div className="mx-auto max-w-3xl space-y-6 p-6">
      <header>
        <h1 className="text-2xl font-bold text-primary">How we price</h1>
        <p className="mt-1 text-sm text-muted">
          The rules behind every quote, in plain English. Your signed Schedule of Rates is the
          authority; prices are CAD, HST extra.
        </p>
      </header>
      <ol className="space-y-4">
        {PRICING_RULES.map((r, i) => (
          <li key={r.title} className="rounded-2xl border border-primary/10 bg-white p-4">
            <h2 className="font-medium text-primary">
              {i + 1}. {r.title}
            </h2>
            <p className="mt-1 text-sm text-gray-700">{r.body}</p>
          </li>
        ))}
      </ol>
      <p className="rounded-xl bg-blue-50 px-4 py-3 text-sm text-blue-900">{PRICING_EXAMPLE}</p>
      <section className="rounded-2xl border border-primary/10 bg-white p-4">
        <h2 className="font-medium text-primary">Your contract</h2>
        {error && <p className="mt-2 text-xs text-red-700">{error}</p>}
        {!error && docs.length === 0 && (
          <p className="mt-2 text-sm text-muted">
            No contract on file yet. Ask PorterChain support.
          </p>
        )}
        <ul className="mt-2 space-y-2">
          {docs.map((d) => (
            <li key={d.id} className="flex items-center justify-between text-sm">
              <span>
                {d.kind_label} · {d.filename}
              </span>
              <button
                type="button"
                className="rounded-lg border border-primary/20 px-3 py-1 text-primary hover:bg-gray-bg"
                onClick={async () => {
                  try {
                    await downloadContractDocument(await getApiToken(), d, orgId ?? undefined);
                  } catch (e) {
                    setError(e instanceof Error ? e.message : "Download failed");
                  }
                }}
              >
                Download
              </button>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
