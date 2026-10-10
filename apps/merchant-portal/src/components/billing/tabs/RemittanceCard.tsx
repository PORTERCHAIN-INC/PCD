"use client";

import { useState } from "react";
import { type BillingOverview } from "@/lib/billing";

function CopyChip({ value, label }: { value: string; label?: string }) {
  const [done, setDone] = useState(false);
  return (
    <button
      type="button"
      onClick={() => {
        void navigator.clipboard?.writeText(value);
        setDone(true);
        window.setTimeout(() => setDone(false), 1500);
      }}
      className="inline-flex min-h-11 items-center gap-2 rounded-xl bg-white/10 px-3 py-2 font-mono text-base font-semibold text-white ring-1 ring-white/25 hover:bg-white/15 focus-visible:outline focus-visible:outline-2 focus-visible:outline-white"
      aria-label={`Copy ${label ?? value}`}
    >
      <span className="break-all">{value}</span>
      <span className="text-xs font-sans font-medium text-white/80">
        {done ? "Copied" : "Copy"}
      </span>
    </button>
  );
}

/** How to pay: Interac e-Transfer to one email, with the PC code in the message. */
export function RemittanceCard({
  remittance,
}: {
  remittance: NonNullable<BillingOverview["remittance"]>;
}) {
  const refs = (remittance.open_references ?? []).filter(Boolean);
  return (
    <section className="rounded-3xl bg-primary p-6 text-white sm:p-8" aria-labelledby="how-to-pay">
      <p
        id="how-to-pay"
        className="text-xs font-semibold uppercase tracking-[0.14em] text-white/80"
      >
        How to pay · Interac e-Transfer
      </p>
      <ol className="mt-5 space-y-5">
        <li>
          <p className="text-sm text-white/80">1. Send to</p>
          <div className="mt-2">
            {remittance.etransfer_email ? (
              <CopyChip value={remittance.etransfer_email} label="e-Transfer email" />
            ) : (
              <span className="text-white">the billing email on your invoice</span>
            )}
          </div>
        </li>
        <li>
          <p className="text-sm text-white/80">2. Put this code in the message</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {refs.length ? (
              refs.map((r) => <CopyChip key={r} value={r} />)
            ) : (
              <span className="font-mono text-white">{remittance.memo}</span>
            )}
          </div>
          {refs.length > 1 ? (
            <p className="mt-2 text-xs text-white/80">One e-Transfer per code matches fastest.</p>
          ) : null}
        </li>
      </ol>
      <p className="mt-6 text-xs leading-relaxed text-white/80">
        Pay to {remittance.payee.replace(/\.$/, "")}. Part payments are applied; anything extra becomes credit on your
        next invoice.
        {remittance.advice_email ? ` Receipts go to ${remittance.advice_email}.` : ""}
      </p>
    </section>
  );
}
