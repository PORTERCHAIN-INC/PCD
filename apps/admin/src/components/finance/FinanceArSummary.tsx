"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { formatCents } from "@porterchain/ui/utils";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { financeApi } from "@/lib/finance";

/** Who owes what, one action each. Reminders are drafts to copy — nothing is sent from here. */
export default function FinanceArSummary() {
  const { getApiToken, isLoaded, isSignedIn } = useAdminAuth();
  const enabled = isLoaded && (isSignedIn || process.env.NODE_ENV === "development");
  const [copied, setCopied] = useState<string | null>(null);
  const q = useQuery({
    queryKey: ["finance-ar-summary"],
    enabled,
    queryFn: async () => financeApi.arSummary(await getApiToken()),
  });
  const d = q.data;
  if (!d || d.items.length === 0) return null;
  const drafts = new Map(d.dunning_drafts.map((x) => [x.merchant_id, x]));

  async function copy(id: string) {
    const draft = drafts.get(id);
    if (!draft) return;
    await navigator.clipboard.writeText(
      `To: ${draft.to ?? ""}\nSubject: ${draft.subject}\n\n${draft.body}`
    );
    setCopied(id);
  }

  return (
    <section className="rounded-2xl border border-primary/10 bg-white p-4">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-sm font-semibold text-primary">Who owes what</h2>
        <p className="text-xs text-muted">
          Owed {formatCents(d.owed_cents)} ·{" "}
          <span className="text-red-700">overdue {formatCents(d.overdue_cents)}</span>
        </p>
      </div>
      <ul className="mt-2 divide-y divide-primary/5">
        {d.items.slice(0, 8).map((m) => (
          <li
            key={m.merchant_id}
            className="flex flex-wrap items-center justify-between gap-2 py-2 text-sm"
          >
            <Link
              href={`/merchants/${m.merchant_id}?tab=billing`}
              className="min-w-0 flex-1 truncate text-primary"
            >
              {m.name}
            </Link>
            <span className="font-mono text-primary">{formatCents(m.outstanding_cents)}</span>
            {m.action === "send_reminder" ? (
              <button
                type="button"
                onClick={() => void copy(m.merchant_id)}
                className="min-h-9 rounded-lg bg-primary px-3 text-xs font-semibold text-white"
              >
                {copied === m.merchant_id
                  ? "Copied"
                  : `Copy reminder (${formatCents(m.overdue_cents)} late)`}
              </button>
            ) : m.action === "invoice_now" ? (
              <span className="text-xs text-muted">
                {formatCents(m.uninvoiced_cents)} not invoiced yet
              </span>
            ) : null}
          </li>
        ))}
      </ul>
    </section>
  );
}
