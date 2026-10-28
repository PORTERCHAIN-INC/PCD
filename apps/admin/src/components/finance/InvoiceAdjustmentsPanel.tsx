"use client";

/**
 * Void, credit lines, or give a partial credit. Every action issues a numbered GST/HST
 * credit note (ETA s.232, SOR/91-44). Rules: docs/compliance/INVOICE_ADJUSTMENTS_CANADA.md.
 */

import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { cn, formatCents } from "@porterchain/ui/utils";
import {
  CREDIT_REASON_LABELS,
  financeApi,
  type CreditNoteKind,
  type CreditNoteResult,
  type CreditNoteRow,
} from "@/lib/finance";
import { downloadOrderFile } from "@/lib/orders";
import { Button } from "@/components/crm/primitives";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { withStaffStepUp } from "@/lib/staff-step-up";

const KIND_LABEL: Record<CreditNoteKind, string> = {
  void: "Void invoice",
  lines: "Credit lines",
  partial: "Partial credit",
};

const SETTLEMENT_LABEL: Record<string, string> = {
  credit_balance: "added to merchant credit balance",
  stripe_refund: "refunded to card",
  stripe_refund_pending: "card refund pending",
  stripe_refund_failed: "card refund failed, retry",
  manual_refund_required: "refund by hand",
};

const STATUS_STYLE: Record<string, string> = {
  issued: "bg-green-100 text-green-700",
  pending_approval: "bg-amber-100 text-amber-800",
  rejected: "bg-gray-100 text-gray-500",
};

export default function InvoiceAdjustmentsPanel({ invoiceId }: { invoiceId: string }) {
  const { getApiToken } = useAdminAuth();
  const qc = useQueryClient();
  const [kind, setKind] = useState<CreditNoteKind>("partial");
  const [reason, setReason] = useState("goodwill");
  const [note, setNote] = useState("");
  const [customerMessage, setCustomerMessage] = useState("");
  const [amount, setAmount] = useState("");
  const [picked, setPicked] = useState<Set<string>>(new Set());
  const [msg, setMsg] = useState<string | null>(null);

  const adj = useQuery({
    queryKey: ["finance-invoice-adjustments", invoiceId],
    queryFn: async () => financeApi.invoiceAdjustments(await getApiToken(), invoiceId),
  });
  const data = adj.data;
  const reasons = data?.reason_codes ?? [];
  const defaultCustomerText = reasons.find((r) => r.code === reason)?.customer_reason ?? "";

  const preview = useMemo(() => {
    if (!data) return 0;
    if (kind === "void") return data.creditable_cents;
    if (kind === "lines")
      return data.lines.filter((l) => picked.has(l.line_id)).reduce((s, l) => s + l.gross_cents, 0);
    return amount.trim() ? Math.round(Number(amount) * 100) : 0;
  }, [data, kind, amount, picked]);
  const needsApproval = !!data && preview > data.approval_threshold_cents;

  async function refresh() {
    await Promise.all(
      [
        ["finance-invoice-adjustments", invoiceId],
        ["finance-invoice", invoiceId],
        ["finance-invoices"],
        ["finance-collections"],
      ].map((queryKey) => qc.invalidateQueries({ queryKey }))
    );
  }

  function describe(res: CreditNoteResult): string {
    if (res.status === "pending_approval")
      return `Credit of ${formatCents(res.amount_cents)} is waiting for a second admin to approve.`;
    const parts = [
      `Credit note ${res.credit_note_number} issued for ${formatCents(res.amount_cents)}`,
    ];
    parts.push(`(tax reversed ${formatCents(res.tax_cents)})`);
    if (res.settlement && res.settlement_cents)
      parts.push(
        `· ${formatCents(res.settlement_cents)} ${SETTLEMENT_LABEL[res.settlement] ?? res.settlement}`
      );
    if (res.email)
      parts.push(res.email.sent ? `· emailed ${res.email.recipient}` : "· email not sent");
    if (res.warning) parts.push("· note: invoice is over 2 years old (tax charged in error limit)");
    return parts.join(" ");
  }

  const createMut = useMutation({
    mutationFn: async () => {
      const token = await getApiToken();
      return withStaffStepUp(token, () =>
        financeApi.createCreditNote(token, invoiceId, {
          kind,
          reason_code: reason,
          internal_note: note.trim() || undefined,
          customer_message: customerMessage.trim() || undefined,
          line_ids: kind === "lines" ? [...picked] : undefined,
          amount_cents: kind === "partial" ? preview : undefined,
        })
      );
    },
    onSuccess: async (res) => {
      setMsg(describe(res));
      setAmount("");
      setNote("");
      setCustomerMessage("");
      setPicked(new Set());
      await refresh();
    },
    onError: (e: Error) => setMsg(e.message || "Credit failed"),
  });

  const decideMut = useMutation({
    mutationFn: async ({ id, action }: { id: string; action: "approve" | "reject" | "retry" }) => {
      const token = await getApiToken();
      return withStaffStepUp(token, () =>
        action === "approve"
          ? financeApi.approveCreditNote(token, id)
          : action === "reject"
            ? financeApi.rejectCreditNote(token, id)
            : financeApi.retryCreditNoteRefund(token, id)
      );
    },
    onSuccess: async (res) => {
      setMsg(res.status === "rejected" ? "Credit request rejected." : describe(res));
      await refresh();
    },
    onError: (e: Error) => setMsg(e.message || "Action failed"),
  });

  async function downloadNote(row: CreditNoteRow) {
    try {
      await downloadOrderFile(
        await getApiToken(),
        `/v1/admin/finance/credit-notes/${row.credit_note_id}/pdf`,
        `${row.credit_note_number}.pdf`
      );
    } catch (err) {
      setMsg(err instanceof Error ? err.message : "Credit note PDF failed");
    }
  }

  if (!data) return null;
  const canCredit = data.creditable_cents > 0;
  const valid =
    preview > 0 &&
    preview <= data.creditable_cents &&
    (reason !== "other" || note.trim().length > 0) &&
    (kind !== "lines" || picked.size > 0);

  function confirmAndSubmit() {
    const what =
      kind === "void"
        ? `Void this invoice and issue a credit note for ${formatCents(preview)}?`
        : `Issue a credit note for ${formatCents(preview)}?`;
    if (confirm(`${what}\n\nThe customer will be emailed a credit note. This cannot be undone.`))
      createMut.mutate();
  }

  return (
    <div className="rounded-2xl border border-primary/10 bg-white p-6">
      <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="font-semibold">Credits &amp; adjustments</h2>
        <span className="text-xs text-muted">
          Credited {formatCents(data.credited_cents)} of {formatCents(data.total_cents)} · tax
          reversed {formatCents(data.tax_credited_cents)} of {formatCents(data.tax_cents)}
        </span>
      </div>

      {data.credit_notes.length ? (
        <ul className="mb-4 divide-y divide-primary/5 text-sm">
          {data.credit_notes.map((n) => (
            <li
              key={n.credit_note_id}
              className="flex flex-wrap items-center justify-between gap-2 py-2"
            >
              <div className="min-w-0">
                <span className="font-mono text-xs text-primary">
                  {n.credit_note_number ?? "(unnumbered)"}
                </span>{" "}
                <span
                  className={cn(
                    "rounded-full px-2 py-0.5 text-xs font-bold",
                    STATUS_STYLE[n.status]
                  )}
                >
                  {n.status.replace(/_/g, " ")}
                </span>
                <p className="text-xs text-muted">
                  {KIND_LABEL[n.kind]} ·{" "}
                  {CREDIT_REASON_LABELS[n.reason_code ?? ""] ?? n.reason_code} ·{" "}
                  {formatCents(n.subtotal_cents)} + tax {formatCents(n.tax_cents)}
                  {n.settlement && n.settlement_cents
                    ? ` · ${formatCents(n.settlement_cents)} ${SETTLEMENT_LABEL[n.settlement] ?? n.settlement}`
                    : ""}
                </p>
                {n.internal_note ? (
                  <p className="text-xs italic text-muted">Internal: {n.internal_note}</p>
                ) : null}
              </div>
              <div className="flex items-center gap-2">
                <span className="font-medium text-primary">−{formatCents(n.amount_cents)}</span>
                {n.status === "issued" ? (
                  <button
                    type="button"
                    className="text-xs text-secondary hover:underline"
                    onClick={() => void downloadNote(n)}
                  >
                    PDF
                  </button>
                ) : null}
                {n.status === "pending_approval" ? (
                  <>
                    <Button
                      variant="outline"
                      disabled={decideMut.isPending}
                      onClick={() => decideMut.mutate({ id: n.credit_note_id, action: "approve" })}
                    >
                      Approve
                    </Button>
                    <Button
                      variant="ghost"
                      disabled={decideMut.isPending}
                      onClick={() => decideMut.mutate({ id: n.credit_note_id, action: "reject" })}
                    >
                      Reject
                    </Button>
                  </>
                ) : null}
                {n.settlement === "stripe_refund_failed" ||
                n.settlement === "stripe_refund_pending" ? (
                  <Button
                    variant="outline"
                    disabled={decideMut.isPending}
                    onClick={() => decideMut.mutate({ id: n.credit_note_id, action: "retry" })}
                  >
                    Retry refund
                  </Button>
                ) : null}
              </div>
            </li>
          ))}
        </ul>
      ) : null}

      {canCredit ? (
        <div className="space-y-3 border-t border-primary/10 pt-4">
          <div className="flex flex-wrap gap-2" role="radiogroup" aria-label="Credit type">
            {(["partial", "lines", "void"] as CreditNoteKind[])
              .filter((k) => k !== "lines" || data.lines.length > 0)
              .map((k) => (
                <button
                  key={k}
                  type="button"
                  role="radio"
                  aria-checked={kind === k}
                  onClick={() => setKind(k)}
                  className={cn(
                    "rounded-full border px-3 py-1 text-sm",
                    kind === k
                      ? "border-secondary bg-secondary/10 text-secondary"
                      : "border-primary/15 text-primary"
                  )}
                >
                  {KIND_LABEL[k]}
                </button>
              ))}
          </div>

          {kind === "partial" ? (
            <input
              aria-label="Credit amount (tax included)"
              inputMode="decimal"
              className="w-full rounded-lg border border-primary/15 px-3 py-2 text-sm"
              placeholder={`Amount incl. tax (max ${formatCents(data.creditable_cents)})`}
              value={amount}
              onChange={(e) => setAmount(e.target.value.replace(/[^0-9.]/g, ""))}
            />
          ) : null}
          {kind === "lines" ? (
            <ul className="space-y-1 text-sm">
              {data.lines.map((l) => (
                <li key={l.line_id}>
                  <label
                    className={cn(
                      "flex items-center justify-between gap-2",
                      l.credited && "opacity-50"
                    )}
                  >
                    <span className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        disabled={l.credited}
                        checked={picked.has(l.line_id)}
                        onChange={(e) => {
                          const next = new Set(picked);
                          if (e.target.checked) next.add(l.line_id);
                          else next.delete(l.line_id);
                          setPicked(next);
                        }}
                      />
                      {l.description} {l.credited ? "(credited)" : ""}
                    </span>
                    <span>
                      {formatCents(l.gross_cents)}{" "}
                      <span className="text-xs text-muted">
                        incl. tax {formatCents(l.tax_cents)}
                      </span>
                    </span>
                  </label>
                </li>
              ))}
            </ul>
          ) : null}
          {kind === "void" ? (
            <p className="text-sm text-muted">
              Credits the full remaining {formatCents(data.creditable_cents)} and marks the invoice
              void. The original invoice is kept, as the law requires.
            </p>
          ) : null}

          <select
            aria-label="Reason"
            className="w-full rounded-lg border border-primary/15 px-3 py-2 text-sm"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
          >
            {Object.entries(CREDIT_REASON_LABELS).map(([code, label]) => (
              <option key={code} value={code}>
                {label}
              </option>
            ))}
          </select>
          <textarea
            aria-label="Internal note"
            className="w-full rounded-lg border border-primary/15 px-3 py-2 text-sm"
            rows={2}
            maxLength={2000}
            placeholder={
              reason === "other"
                ? "Internal note (required)"
                : "Internal note (staff only, never sent)"
            }
            value={note}
            onChange={(e) => setNote(e.target.value)}
          />
          <textarea
            aria-label="Message to customer"
            className="w-full rounded-lg border border-primary/15 px-3 py-2 text-sm"
            rows={2}
            maxLength={500}
            placeholder={`Customer sees: “${defaultCustomerText}”`}
            value={customerMessage}
            onChange={(e) => setCustomerMessage(e.target.value)}
          />
          <div className="flex flex-wrap items-center gap-3">
            <Button
              variant={kind === "void" ? "danger" : "primary"}
              disabled={!valid || createMut.isPending}
              onClick={confirmAndSubmit}
            >
              {createMut.isPending
                ? "Issuing…"
                : needsApproval
                  ? `Request approval for ${formatCents(preview)}`
                  : `Issue credit note ${preview ? formatCents(preview) : ""}`}
            </Button>
            {needsApproval ? (
              <span className="text-xs text-amber-800">
                Over {formatCents(data.approval_threshold_cents)}: a second admin must approve.
              </span>
            ) : null}
          </div>
          <p className="text-xs text-muted">
            Issues a numbered GST/HST credit note (Excise Tax Act s. 232) that reverses the tax this
            invoice charged, and emails it to the customer. Any amount already paid above the new
            total goes to the merchant&apos;s credit balance or back to the card.
          </p>
        </div>
      ) : (
        <p className="text-sm text-muted">Nothing left to credit on this invoice.</p>
      )}
      {msg && <p className="mt-3 text-xs text-secondary">{msg}</p>}
    </div>
  );
}
