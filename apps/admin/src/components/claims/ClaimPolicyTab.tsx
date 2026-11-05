"use client";

import { useState } from "react";
import { formatCents } from "@porterchain/ui/utils";
import { Badge, Button } from "@/components/crm/primitives";
import type { ClaimDetail, ClaimLetter, ClaimPolicy } from "@/lib/claims";

export type PolicyActions = {
  onDraftLetter: (body: {
    kind: string;
    amount_cents?: number;
    reason?: string;
    details?: string;
  }) => Promise<ClaimLetter>;
  onPrepareBrokerNotice: () => Promise<ClaimLetter>;
  onRecordBrokerNotified: (body: { sent_on: string; method: string }) => Promise<unknown>;
};

/**
 * Cargo policy (Lloyd's B5000191409) and O. Reg. 643/05 view of a claim. Letters and the broker
 * notice are drafts: the admin copies and sends them. Nothing is sent from here.
 */
export default function ClaimPolicyTab({
  detail,
  actions,
}: {
  detail: ClaimDetail;
  actions: PolicyActions;
}) {
  const p = (detail.policy ?? {}) as ClaimPolicy;
  const [draft, setDraft] = useState<ClaimLetter | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function run(fn: () => Promise<ClaimLetter>) {
    setError(null);
    try {
      setDraft(await fn());
    } catch (e) {
      setError(e instanceof Error ? e.message.replace(/_/g, " ") : "Could not prepare the draft");
    }
  }

  if (!p.applies) {
    return (
      <p className="text-sm text-muted">
        This claim type is not a cargo loss or damage claim, so the cargo policy limits do not
        apply.
      </p>
    );
  }
  const notice = p.notice ?? {};
  const ins = p.insurer ?? {};
  const bn = p.broker_notice;

  return (
    <div className="space-y-6 text-sm">
      <section>
        <h3 className="font-bold text-primary">Limits</h3>
        <p className="mt-1">
          Most we can pay on this shipment:{" "}
          <strong>{formatCents(Number(p.liability?.cap_cents ?? 0))}</strong> (policy limit{" "}
          {formatCents(Number(p.liability?.limit_cents ?? 0))}). Standard liability is $4.41/kg
          unless declared-value cover was bought. The{" "}
          {formatCents(Number(ins.deductible_cents ?? 0))} deductible is PorterChain&apos;s cost and
          is never charged to the merchant.
        </p>
      </section>

      <section>
        <h3 className="font-bold text-primary">Notice deadline (O. Reg. 643/05)</h3>
        <p className="mt-1">
          {notice.rule ?? "—"} · deadline {notice.deadline ?? "unknown"}{" "}
          {notice.within_time === true ? (
            <Badge tone="green">In time</Badge>
          ) : notice.within_time === false ? (
            <Badge tone="red">Late</Badge>
          ) : (
            <Badge tone="amber">Check dates</Badge>
          )}
        </p>
      </section>

      <section>
        <h3 className="font-bold text-primary">Evidence</h3>
        <ul className="mt-1 space-y-1">
          {(p.evidence?.items ?? []).map((i) => (
            <li key={i.key}>
              {i.received ? "✓" : "✗"} {i.label}
            </li>
          ))}
        </ul>
      </section>

      <section>
        <h3 className="font-bold text-primary">Insurer</h3>
        <p className="mt-1">
          {ins.notify_broker
            ? "The claim may exceed the deductible. Prepare a notice for Able Insurance Brokers and send it yourself."
            : "Within the deductible: PorterChain handles it directly; no broker notice needed."}
        </p>
        {bn ? (
          <p className="mt-1 text-muted">
            Broker notice:{" "}
            {bn.sent ? `sent ${bn.sent_on ?? ""} by ${bn.method ?? ""}` : "drafted, not sent"}
          </p>
        ) : null}
        <div className="mt-2 flex flex-wrap gap-2">
          <Button variant="outline" onClick={() => void run(actions.onPrepareBrokerNotice)}>
            Draft broker notice
          </Button>
          {bn && !bn.sent ? (
            <Button
              variant="outline"
              onClick={() => {
                const method = prompt("How did you send it? (email or phone)");
                if (!method) return;
                const sentOn = new Date().toISOString().slice(0, 10);
                void actions
                  .onRecordBrokerNotified({ sent_on: sentOn, method })
                  .catch(() => setError("Could not record it"));
              }}
            >
              I sent it to the broker
            </Button>
          ) : null}
        </div>
      </section>

      <section>
        <h3 className="font-bold text-primary">Letters</h3>
        <p className="mt-1 text-muted">
          Drafts only. No liability is admitted before the investigation is done.
        </p>
        <div className="mt-2 flex flex-wrap gap-2">
          <Button
            variant="outline"
            onClick={() => void run(() => actions.onDraftLetter({ kind: "acknowledgement" }))}
          >
            Acknowledgement
          </Button>
          <Button
            variant="outline"
            disabled={!p.investigated}
            onClick={() => {
              const dollars = prompt("Amount to pay ($)");
              if (!dollars) return;
              void run(() =>
                actions.onDraftLetter({
                  kind: "approved",
                  amount_cents: Math.round(Number(dollars) * 100),
                })
              );
            }}
          >
            Decision: pay
          </Button>
          <select
            className="rounded-lg border border-primary/10 px-2 py-1"
            disabled={!p.investigated}
            defaultValue=""
            aria-label="Denial reason"
            onChange={(e) => {
              const reason = e.target.value;
              e.target.value = "";
              if (reason) void run(() => actions.onDraftLetter({ kind: "denied", reason }));
            }}
          >
            <option value="">Decision: deny (choose reason)…</option>
            {(p.denial_reasons ?? []).map((r) => (
              <option key={r.key} value={r.key}>
                {r.key.replace(/_/g, " ")}
              </option>
            ))}
          </select>
        </div>
      </section>

      {error ? <p className="text-red-600">{error}</p> : null}
      {draft ? (
        <section className="rounded-xl border border-primary/10 p-4">
          {draft.to ? <p className="text-muted">To: {draft.to}</p> : null}
          <p className="font-bold">{draft.subject}</p>
          <pre className="mt-2 whitespace-pre-wrap font-sans">{draft.body}</pre>
          <Button
            variant="outline"
            className="mt-2"
            onClick={() => void navigator.clipboard.writeText(`${draft.subject}\n\n${draft.body}`)}
          >
            Copy
          </Button>
        </section>
      ) : null}
    </div>
  );
}
