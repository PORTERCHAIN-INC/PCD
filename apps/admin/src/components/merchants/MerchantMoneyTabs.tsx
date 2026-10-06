"use client";

import { useState } from "react";
import Link from "next/link";
import { cn } from "@porterchain/ui/utils";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { useApiData } from "@/hooks/useApiData";
import { merchants, merchantActionMessage } from "@/lib/merchants";
import { financeApi } from "@/lib/finance";
import { withStaffStepUp } from "@/lib/staff-step-up";
import { ListPager } from "@/components/crm/ListPager";
import { Badge, Button, Field, Input, Select, SectionCard } from "@/components/crm/primitives";
import { money, shortDate, titleCase, dateTime } from "@/lib/crmFormat";
import { PageSkeleton } from "@porterchain/ui/loading";

const CONTRACT_STATUSES = ["draft", "active", "expired", "cancelled"] as const;
const TERMS = ["IMMEDIATE", "NET_7", "NET_14", "NET_15", "NET_30", "NET_45", "CUSTOM"];

function Metric({
  label,
  value,
  sub,
  danger,
}: {
  label: string;
  value: string;
  sub?: string;
  danger?: boolean;
}) {
  return (
    <div className="min-w-0 rounded-xl border border-primary/10 p-4">
      <p className="text-xs text-muted">{label}</p>
      <p className="mt-1 truncate text-xl font-bold tabular-nums text-primary">{value}</p>
      {sub && <p className={cn("text-xs", danger ? "text-red-600" : "text-muted")}>{sub}</p>}
    </div>
  );
}

export function StatementTab({ id }: { id: string }) {
  const { data, error } = useApiData((t) => merchants.statement(t, id), [id], {
    key: `merchant-statement-${id}`,
  });
  if (error) {
    return (
      <SectionCard title="Current billing period">
        <p className="px-5 py-4 text-sm text-red-600">{error}</p>
      </SectionCard>
    );
  }
  if (!data) {
    return (
      <SectionCard title="Current billing period">
        <div className="px-5 py-4">
          <PageSkeleton rows={3} />
        </div>
      </SectionCard>
    );
  }
  return (
    <SectionCard title="Current billing period">
      <div className="space-y-3 px-5 py-4 text-sm">
        <p className="text-xs text-muted">
          {shortDate(data.period_start)} → {shortDate(data.period_end)} ·{" "}
          {titleCase(data.billing_cycle)} · {titleCase(data.payment_terms)} ({data.net_terms_days}{" "}
          days)
        </p>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <Metric label="Outstanding" value={money(data.outstanding_balance_cents)} />
          <Metric label="Invoiced AR" value={money(data.outstanding_invoices_cents)} />
          <Metric label="Uninvoiced" value={money(data.uninvoiced_orders_cents)} />
          <Metric label="Credit notes" value={money(data.credit_notes_cents)} />
          <Metric label="Period orders" value={String(data.monthly_orders)} />
          <Metric label="Period spend" value={money(data.monthly_spend_cents)} />
        </div>
        <p className="text-xs text-muted">
          Stripe checkout {data.stripe_enabled ? "enabled" : "off"} for this company. Detailed line
          CSV stays on the merchant portal Billing → Statement export.
        </p>
      </div>
    </SectionCard>
  );
}

export function InvoicesTab({ id }: { id: string }) {
  const { getApiToken } = useAdminAuth();
  const { data, refetch } = useApiData((t) => merchants.invoices(t, id), [id], {
    key: `merchant-invoices-${id}`,
  });
  const [busy, setBusy] = useState<"preview" | "generate" | null>(null);
  const [remindingId, setRemindingId] = useState<string | null>(null);
  const [preview, setPreview] = useState<Awaited<ReturnType<typeof merchants.arPreview>> | null>(
    null
  );
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const outstanding = (data ?? [])
    .filter((i) => i.status !== "paid" && i.status !== "void")
    .reduce((s, i) => s + i.total_cents, 0);

  async function runPreview() {
    setBusy("preview");
    setError(null);
    try {
      const token = await getApiToken();
      setPreview(await merchants.arPreview(token, id));
      setMessage(null);
    } catch (e) {
      setError(merchantActionMessage(e, "Could not preview invoices"));
    } finally {
      setBusy(null);
    }
  }

  async function runGenerate() {
    if (
      !window.confirm(
        "Create invoices for delivered / POD orders in the last closed billing cycle?"
      )
    ) {
      return;
    }
    setBusy("generate");
    setError(null);
    try {
      const token = await getApiToken();
      const result = await merchants.arGenerate(token, id);
      setMessage(
        `Created ${result.created_count} invoice(s); skipped ${result.skipped_count} already billed.`
      );
      setPreview(null);
      void refetch();
    } catch (e) {
      setError(merchantActionMessage(e, "Could not generate invoices"));
    } finally {
      setBusy(null);
    }
  }

  async function runRemind(invoiceId: string) {
    setRemindingId(invoiceId);
    setError(null);
    try {
      const token = await getApiToken();
      const result = await withStaffStepUp(token, () => financeApi.remindInvoice(token, invoiceId));
      setMessage(`Reminder sent to ${result.email} for ${result.invoice_number}.`);
      void refetch();
    } catch (e) {
      setError(merchantActionMessage(e, "Could not send reminder"));
    } finally {
      setRemindingId(null);
    }
  }

  return (
    <SectionCard
      title="Delivery invoices (ops AR)"
      action={
        <span className="text-sm text-muted">
          Outstanding <span className="font-bold text-primary">{money(outstanding)}</span>
        </span>
      }
    >
      <div className="space-y-3 border-b border-primary/5 px-4 py-3 sm:px-5">
        <p className="text-xs text-muted">
          Generate covers delivered and POD orders in the last closed cycle for this company. Leave
          Finance for cross-merchant runs and recording payments.
        </p>
        <div className="flex flex-wrap items-center gap-2">
          <Button variant="outline" disabled={busy !== null} onClick={() => void runPreview()}>
            {busy === "preview" ? "Previewing…" : "Preview cycle"}
          </Button>
          <Button disabled={busy !== null} onClick={() => void runGenerate()}>
            {busy === "generate" ? "Generating…" : "Generate invoices"}
          </Button>
        </div>
        {preview && (
          <p className="text-sm text-primary">
            {preview.order_count} order(s) · {money(preview.uninvoiced_cents)} uninvoiced ·{" "}
            {titleCase(preview.payment_terms || "terms")} · {preview.billing_cycle || "cycle"}
          </p>
        )}
        {message && <p className="text-sm text-secondary">{message}</p>}
        {error && <p className="text-sm text-red-600">{error}</p>}
      </div>
      <div className="divide-y divide-primary/5">
        {(data ?? []).map((inv) => {
          const remindable =
            inv.status === "overdue" || inv.status === "sent" || inv.status === "pending";
          return (
            <div
              key={inv.id}
              className="flex min-w-0 flex-wrap items-center justify-between gap-2 px-4 py-3 sm:px-5"
            >
              <div>
                <p className="text-sm font-medium text-primary">
                  <Link
                    href={`/finance/invoices/${inv.id}`}
                    className="text-secondary hover:underline"
                  >
                    {inv.invoice_number}
                  </Link>
                </p>
                <p className="text-xs text-muted">
                  {money(inv.total_cents)} · {titleCase(inv.net_terms)} · due{" "}
                  {shortDate(inv.due_date)}
                </p>
              </div>
              <div className="flex items-center gap-2">
                {remindable ? (
                  <Button
                    variant="outline"
                    disabled={remindingId !== null || busy !== null}
                    onClick={() => void runRemind(inv.id)}
                  >
                    {remindingId === inv.id ? "Sending…" : "Remind"}
                  </Button>
                ) : null}
                <Badge
                  tone={
                    inv.status === "paid" ? "green" : inv.status === "overdue" ? "red" : "amber"
                  }
                >
                  {titleCase(inv.status)}
                </Badge>
              </div>
            </div>
          );
        })}
        {(!data || data.length === 0) && (
          <p className="px-5 py-10 text-center text-sm text-muted">No invoices yet.</p>
        )}
      </div>
    </SectionCard>
  );
}

export function CreditNotesTab({ id }: { id: string }) {
  const { data } = useApiData((t) => merchants.creditNotes(t, id), [id], {
    key: `merchant-credits-${id}`,
  });
  return (
    <SectionCard title="Credit notes">
      <div className="divide-y divide-primary/5">
        {(data ?? []).map((c) => (
          <div key={c.credit_note_id} className="flex items-center justify-between gap-3 px-5 py-3">
            <div className="min-w-0">
              <p className="text-sm font-medium text-primary">
                {c.order_number ?? c.credit_note_id.slice(0, 8)}
              </p>
              <p className="text-xs text-muted">
                {c.reason ?? "Credit note"}
                {c.tracking_number ? ` · ${c.tracking_number}` : ""}
                {c.created_at ? ` · ${shortDate(c.created_at)}` : ""}
              </p>
            </div>
            <div className="text-right">
              <p className="text-sm font-semibold text-primary">{money(c.amount_cents)}</p>
              <Badge tone={c.status === "applied" || c.status === "issued" ? "green" : "slate"}>
                {titleCase(c.status)}
              </Badge>
            </div>
          </div>
        ))}
        {(!data || data.length === 0) && (
          <p className="px-5 py-10 text-center text-sm text-muted">
            No credit notes on file. Credits reduce outstanding AR on the statement.
          </p>
        )}
      </div>
    </SectionCard>
  );
}

export function ContractsTab({ id }: { id: string }) {
  const { getApiToken } = useAdminAuth();
  const { data, refetch } = useApiData((t) => merchants.contracts(t, id), [id], {
    key: `merchant-contracts-${id}`,
  });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [terms, setTerms] = useState("NET_30");
  const [value, setValue] = useState(0);
  const [editId, setEditId] = useState<string | null>(null);
  const [editStatus, setEditStatus] = useState("draft");
  const [editTerms, setEditTerms] = useState("NET_30");
  const [editValue, setEditValue] = useState(0);

  async function createContract() {
    setBusy(true);
    setError(null);
    try {
      const token = await getApiToken();
      await merchants.createContract(token, id, {
        net_terms: terms,
        value_cents: Math.round(Number(value) * 100) || 0,
      });
      void refetch();
    } catch (e) {
      setError(merchantActionMessage(e instanceof Error ? e.message : "Create failed"));
    } finally {
      setBusy(false);
    }
  }

  async function saveAmend(contractId: string) {
    setBusy(true);
    setError(null);
    try {
      const token = await getApiToken();
      await merchants.updateContract(token, id, contractId, {
        status: editStatus,
        net_terms: editTerms,
        value_cents: Math.round(Number(editValue) * 100) || 0,
      });
      setEditId(null);
      void refetch();
    } catch (e) {
      setError(merchantActionMessage(e instanceof Error ? e.message : "Update failed"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-5">
      <SectionCard title="New contract">
        <div className="grid grid-cols-2 gap-4 p-5">
          <Field label="Net terms">
            <Select value={terms} onChange={(e) => setTerms(e.target.value)}>
              {TERMS.map((t) => (
                <option key={t} value={t}>
                  {titleCase(t)}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Value ($)">
            <Input
              type="number"
              step="0.01"
              value={value}
              onChange={(e) => setValue(Number(e.target.value))}
            />
          </Field>
          <div className="col-span-2 flex items-center gap-3">
            <Button onClick={() => void createContract()} disabled={busy}>
              {busy ? "Creating…" : "Create contract"}
            </Button>
            {error && <span className="text-sm text-red-600">{error}</span>}
          </div>
          <p className="col-span-2 text-xs text-muted">
            Requires a linked CRM company (convert lead → merchant). Draft contract is created for
            that company.
          </p>
        </div>
      </SectionCard>
      <SectionCard title="Contracts">
        <div className="divide-y divide-primary/5">
          {(data ?? []).map((c) => (
            <div key={c.id} className="px-5 py-3">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-sm font-medium text-primary">{c.contract_number}</p>
                  <p className="text-xs text-muted">
                    {titleCase(c.net_terms)} · {money(c.value_cents)} · expires{" "}
                    {shortDate(c.expiry_date)}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <Badge tone={c.status === "active" ? "green" : "slate"}>
                    {titleCase(c.status)}
                  </Badge>
                  <Button
                    variant="outline"
                    className="text-xs"
                    onClick={() => {
                      setEditId(editId === c.id ? null : c.id);
                      setEditStatus(c.status);
                      setEditTerms(c.net_terms);
                      setEditValue((c.value_cents || 0) / 100);
                    }}
                  >
                    {editId === c.id ? "Close" : "Amend"}
                  </Button>
                </div>
              </div>
              {editId === c.id && (
                <div className="mt-3 grid grid-cols-3 gap-3 rounded-xl border border-primary/10 bg-gray-bg/40 p-3">
                  <Field label="Status">
                    <Select value={editStatus} onChange={(e) => setEditStatus(e.target.value)}>
                      {CONTRACT_STATUSES.map((s) => (
                        <option key={s} value={s}>
                          {titleCase(s)}
                        </option>
                      ))}
                    </Select>
                  </Field>
                  <Field label="Net terms">
                    <Select value={editTerms} onChange={(e) => setEditTerms(e.target.value)}>
                      {TERMS.map((t) => (
                        <option key={t} value={t}>
                          {titleCase(t)}
                        </option>
                      ))}
                    </Select>
                  </Field>
                  <Field label="Value ($)">
                    <Input
                      type="number"
                      step="0.01"
                      value={editValue}
                      onChange={(e) => setEditValue(Number(e.target.value))}
                    />
                  </Field>
                  <div className="col-span-3">
                    <Button onClick={() => void saveAmend(c.id)} disabled={busy}>
                      {busy ? "Saving…" : "Save amend"}
                    </Button>
                  </div>
                </div>
              )}
            </div>
          ))}
          {(!data || data.length === 0) && (
            <p className="px-5 py-10 text-center text-sm text-muted">No contracts yet.</p>
          )}
        </div>
      </SectionCard>
    </div>
  );
}
