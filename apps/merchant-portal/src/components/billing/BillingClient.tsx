"use client";

import Button from "@/components/ui/Button";
import { useMerchantAuth } from "@/hooks/useMerchantAuth";
import {
  billingApi,
  formatCycle,
  formatTerms,
  STATUS_STYLES,
  type BillingHistoryRow,
  type BillingOverview,
  type CreditNoteRow,
  type InvoiceRow,
  type PaymentRow,
  type StatementDetail,
} from "@/lib/billing";
import { publicEnv } from "@/lib/env";
import { formatCents, formatDate } from "@/lib/utils";
import { useCallback, useEffect, useState } from "react";

type Tab = "overview" | "invoices" | "statement" | "payments" | "credits" | "history" | "tax";

const TABS: { id: Tab; label: string }[] = [
  { id: "overview", label: "Overview" },
  { id: "invoices", label: "Invoices" },
  { id: "statement", label: "Statement" },
  { id: "payments", label: "Payment history" },
  { id: "credits", label: "Credit notes" },
  { id: "history", label: "History" },
  { id: "tax", label: "Tax summary" },
];

export default function BillingClient() {
  const { getApiToken, orgId, isLoaded, isSignedIn } = useMerchantAuth();
  const [tab, setTab] = useState<Tab>("overview");
  const [overview, setOverview] = useState<BillingOverview | null>(null);
  const [invoices, setInvoices] = useState<InvoiceRow[]>([]);
  const [statement, setStatement] = useState<StatementDetail | null>(null);
  const [payments, setPayments] = useState<PaymentRow[]>([]);
  const [credits, setCredits] = useState<CreditNoteRow[]>([]);
  const [history, setHistory] = useState<BillingHistoryRow[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    if (!isSignedIn) return;
    setLoading(true);
    setError(null);
    try {
      const token = await getApiToken();
      const [ov, inv, stmt, pay, cr, hist] = await Promise.all([
        billingApi.overview(token, orgId),
        billingApi.invoices(token, orgId),
        billingApi.statementDetail(token, orgId),
        billingApi.payments(token, orgId),
        billingApi.creditNotes(token, orgId),
        billingApi.history(token, orgId),
      ]);
      setOverview(ov);
      setInvoices(inv);
      setStatement(stmt);
      setPayments(pay);
      setCredits(cr);
      setHistory(hist);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load billing");
    } finally {
      setLoading(false);
    }
  }, [getApiToken, isSignedIn, orgId]);

  useEffect(() => {
    if (!isLoaded || !isSignedIn) return;
    void load();
  }, [isLoaded, isSignedIn, load]);

  async function download(kind: "invoices" | "statement" | "history") {
    const token = await getApiToken();
    if (kind === "invoices") await billingApi.downloadInvoicesCsv(token, orgId);
    else if (kind === "statement") await billingApi.downloadStatementCsv(token, orgId);
    else await billingApi.downloadHistoryCsv(token, orgId);
  }

  if (error && !overview) return <p className="text-red-600">{error}</p>;
  if (!overview) return <p className="text-muted">{loading ? "Loading billing…" : "Loading…"}</p>;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-primary">Billing</h1>
          <p className="text-sm text-muted">
            {formatTerms(overview.payment_terms)} · {formatCycle(overview.billing_cycle)} cycle
            {!overview.stripe_enabled && " · Net terms (no Stripe)"}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button size="sm" variant="outline" onClick={() => void download("invoices")}>
            Export invoices CSV
          </Button>
          <Button size="sm" variant="outline" onClick={() => void download("statement")}>
            Export statement CSV
          </Button>
          <Button size="sm" variant="outline" onClick={() => void download("history")}>
            Export history CSV
          </Button>
        </div>
      </div>

      <nav className="flex flex-wrap gap-1 border-b border-primary/10 pb-1">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setTab(t.id)}
            className={`rounded-lg px-3 py-1.5 text-sm ${
              tab === t.id
                ? "bg-secondary/10 font-semibold text-secondary"
                : "text-muted hover:text-primary"
            }`}
          >
            {t.label}
          </button>
        ))}
      </nav>

      {tab === "overview" && <OverviewTab overview={overview} />}
      {tab === "invoices" && (
        <InvoicesTab invoices={invoices} orgId={orgId} getToken={getApiToken} />
      )}
      {tab === "statement" && statement && <StatementTab statement={statement} />}
      {tab === "payments" && (
        <PaymentsTab payments={payments} stripeEnabled={overview.stripe_enabled} />
      )}
      {tab === "credits" && <CreditsTab credits={credits} />}
      {tab === "history" && <HistoryTab history={history} />}
      {tab === "tax" && <TaxTab overview={overview} />}
    </div>
  );
}

function OverviewTab({ overview }: { overview: BillingOverview }) {
  const cp = overview.contract_pricing;
  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Kpi label="Outstanding balance" value={formatCents(overview.outstanding_balance_cents)} />
        <Kpi
          label="Invoiced outstanding"
          value={formatCents(overview.outstanding_invoices_cents)}
        />
        <Kpi label="Uninvoiced orders" value={formatCents(overview.uninvoiced_orders_cents)} />
        {(overview.credit_notes_cents ?? 0) > 0 && (
          <Kpi label="Credit notes" value={`−${formatCents(overview.credit_notes_cents!)}`} />
        )}
        <Kpi label="Period spend" value={formatCents(overview.monthly_spend_cents)} />
        <Kpi label="Invoices due" value={String(overview.invoices_due)} />
        <Kpi label="Overdue" value={String(overview.overdue_invoices)} />
        <Kpi label="Net terms" value={`${overview.net_terms_days} days`} />
        <Kpi
          label="Credit limit"
          value={
            overview.credit_limit_cents != null ? formatCents(overview.credit_limit_cents) : "—"
          }
        />
      </div>

      {overview.period_start && (
        <p className="text-sm text-muted">
          Current billing period: {formatDate(overview.period_start)} —{" "}
          {formatDate(overview.period_end || "")}
        </p>
      )}

      {cp.has_contract && (
        <section className="rounded-2xl border border-primary/10 bg-white p-5">
          <h2 className="font-semibold text-primary">Contract pricing</h2>
          <p className="mt-1 text-sm">
            {cp.contract_name} · Min commitment {formatCents(cp.minimum_monthly_commitment_cents)}
          </p>
          {cp.effective_from && (
            <p className="text-xs text-muted">
              Effective {formatDate(cp.effective_from)}
              {cp.effective_to ? ` — ${formatDate(cp.effective_to)}` : ""}
            </p>
          )}
        </section>
      )}
    </div>
  );
}

function InvoicesTab({
  invoices,
  orgId,
  getToken,
}: {
  invoices: InvoiceRow[];
  orgId?: string;
  getToken: () => Promise<string>;
}) {
  async function openPdf(invoiceId: string, pdfUrl?: string | null) {
    if (pdfUrl) {
      window.open(pdfUrl, "_blank", "noopener,noreferrer");
      return;
    }
    const token = await getToken();
    const url = `${publicEnv.porterchainApiUrl}/v1/merchant/billing/invoices/${invoiceId}/pdf`;
    const response = await fetch(url, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
      redirect: "follow",
    });
    if (response.ok && response.url) window.open(response.url, "_blank", "noopener,noreferrer");
  }

  if (!invoices.length) {
    return (
      <p className="text-sm text-muted">No invoices yet — net terms orders appear when invoiced.</p>
    );
  }

  return (
    <div className="overflow-x-auto rounded-2xl border border-primary/10 bg-white">
      <table className="w-full min-w-[720px] text-left text-sm">
        <thead>
          <tr className="border-b border-primary/10 text-muted">
            <th className="px-4 py-3">Invoice</th>
            <th className="px-4 py-3">Order</th>
            <th className="px-4 py-3">Status</th>
            <th className="px-4 py-3">Amount</th>
            <th className="px-4 py-3">Due</th>
            <th className="px-4 py-3">PDF</th>
          </tr>
        </thead>
        <tbody>
          {invoices.map((inv) => (
            <tr key={inv.invoice_id} className="border-b border-primary/5">
              <td className="px-4 py-3 font-mono text-xs">{inv.invoice_number}</td>
              <td className="px-4 py-3">{inv.order_number ?? "—"}</td>
              <td className="px-4 py-3">
                <StatusBadge status={inv.status} />
              </td>
              <td className="px-4 py-3">
                {formatCents(inv.amount_cents, inv.currency.toUpperCase())}
                {inv.outstanding_cents > 0 && inv.status !== "paid" && (
                  <span className="ml-1 text-xs text-muted">
                    ({formatCents(inv.outstanding_cents)} due)
                  </span>
                )}
              </td>
              <td className="px-4 py-3">{inv.due_date ? formatDate(inv.due_date) : "—"}</td>
              <td className="px-4 py-3">
                {(inv.pdf_url || inv.stripe_receipt_url) && (
                  <button
                    type="button"
                    className="text-secondary hover:underline"
                    onClick={() =>
                      void openPdf(inv.invoice_id, inv.pdf_url || inv.stripe_receipt_url)
                    }
                  >
                    Download PDF
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function StatementTab({ statement }: { statement: StatementDetail }) {
  return (
    <div className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-3">
        <Kpi label="Period orders" value={String(statement.monthly_orders)} />
        <Kpi label="Period spend" value={formatCents(statement.monthly_spend_cents)} />
        <Kpi label="Line items total" value={formatCents(statement.line_items_total_cents)} />
      </div>
      <div className="overflow-x-auto rounded-2xl border border-primary/10 bg-white">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-primary/10 text-muted">
              <th className="px-4 py-3">Type</th>
              <th className="px-4 py-3">Reference</th>
              <th className="px-4 py-3">Description</th>
              <th className="px-4 py-3">Amount</th>
              <th className="px-4 py-3">Status</th>
            </tr>
          </thead>
          <tbody>
            {statement.line_items.map((line, i) => (
              <tr key={i} className="border-b border-primary/5">
                <td className="px-4 py-3 capitalize">{String(line.type)}</td>
                <td className="px-4 py-3 font-mono text-xs">{String(line.reference ?? "—")}</td>
                <td className="px-4 py-3">{String(line.description ?? "")}</td>
                <td className="px-4 py-3">{formatCents(Number(line.amount_cents) || 0)}</td>
                <td className="px-4 py-3">
                  {line.status ? <StatusBadge status={String(line.status)} /> : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function PaymentsTab({
  payments,
  stripeEnabled,
}: {
  payments: PaymentRow[];
  stripeEnabled: boolean;
}) {
  if (!payments.length) {
    return (
      <p className="text-sm text-muted">
        No payments recorded{stripeEnabled ? "" : " — contract merchants settle on net terms"}.
      </p>
    );
  }
  return (
    <table className="w-full rounded-2xl border border-primary/10 bg-white text-left text-sm">
      <thead>
        <tr className="border-b border-primary/10 text-muted">
          <th className="px-4 py-3">Reference</th>
          <th className="px-4 py-3">Order</th>
          <th className="px-4 py-3">Method</th>
          <th className="px-4 py-3">Status</th>
          <th className="px-4 py-3">Amount</th>
          <th className="px-4 py-3">Date</th>
        </tr>
      </thead>
      <tbody>
        {payments.map((p) => (
          <tr key={p.payment_id} className="border-b border-primary/5">
            <td className="px-4 py-3 font-mono text-xs">
              {p.payment_reference ?? p.payment_id.slice(0, 8)}
            </td>
            <td className="px-4 py-3">{p.order_number ?? "—"}</td>
            <td className="px-4 py-3">{p.payment_method ?? "—"}</td>
            <td className="px-4 py-3">
              <StatusBadge status={p.status.toLowerCase()} />
            </td>
            <td className="px-4 py-3">{formatCents(p.amount_cents, p.currency.toUpperCase())}</td>
            <td className="px-4 py-3">{p.created_at ? formatDate(p.created_at) : "—"}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function CreditsTab({ credits }: { credits: CreditNoteRow[] }) {
  if (!credits.length) return <p className="text-sm text-muted">No credit notes on file.</p>;
  return (
    <ul className="space-y-3">
      {credits.map((c) => (
        <li
          key={c.credit_note_id}
          className="rounded-xl border border-primary/10 bg-white p-4 text-sm"
        >
          <p className="font-medium">{c.order_number ?? c.credit_note_id.slice(0, 8)}</p>
          <p className="text-muted">{c.reason ?? "Credit note"}</p>
          <p className="mt-1">{c.amount_cents != null ? formatCents(c.amount_cents) : "—"}</p>
        </li>
      ))}
    </ul>
  );
}

function HistoryTab({ history }: { history: BillingHistoryRow[] }) {
  if (!history.length) return <p className="text-sm text-muted">No billing history yet.</p>;
  return (
    <ul className="divide-y divide-primary/10 rounded-2xl border border-primary/10 bg-white">
      {history.map((h) => (
        <li
          key={`${h.kind}-${h.id}`}
          className="flex items-center justify-between gap-4 px-4 py-3 text-sm"
        >
          <div>
            <p className="font-medium capitalize">{h.kind.replace("_", " ")}</p>
            <p className="text-muted">{h.description}</p>
          </div>
          <div className="text-right">
            <p className={h.amount_cents < 0 ? "text-green-700" : ""}>
              {formatCents(Math.abs(h.amount_cents))}
            </p>
            <p className="text-xs text-muted">
              {h.occurred_at ? formatDate(String(h.occurred_at)) : ""}
            </p>
          </div>
        </li>
      ))}
    </ul>
  );
}

function TaxTab({ overview }: { overview: BillingOverview }) {
  const tax = overview.tax_summary;
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <Kpi label="Subtotal" value={formatCents(tax.subtotal_cents, tax.currency.toUpperCase())} />
      <Kpi label="Tax (HST/GST)" value={formatCents(tax.tax_cents, tax.currency.toUpperCase())} />
      <Kpi label="Fees" value={formatCents(tax.fees_cents, tax.currency.toUpperCase())} />
      <Kpi
        label="Total invoiced"
        value={formatCents(tax.total_cents, tax.currency.toUpperCase())}
      />
    </div>
  );
}

function Kpi({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-primary/10 bg-white p-5">
      <p className="text-sm text-muted">{label}</p>
      <p className="mt-2 text-xl font-bold text-primary">{value}</p>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const style = STATUS_STYLES[status] ?? "bg-gray-100 text-gray-700";
  return <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${style}`}>{status}</span>;
}
