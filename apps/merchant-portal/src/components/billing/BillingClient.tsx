"use client";

import { BillingContactsPanel } from "@/components/billing/BillingContactsPanel";
import { RateCardPanel } from "@/components/billing/RateCardPanel";
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
import { invoiceStatusLabel, paymentStatusLabel } from "@/lib/catalog";
import { settingsApi, type BillingContact } from "@/lib/settings";
import { formatCents, formatDate } from "@/lib/utils";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

type Tab =
  | "overview"
  | "invoices"
  | "statement"
  | "payments"
  | "credits"
  | "history"
  | "tax"
  | "rates"
  | "contacts"
  | "cod";

const TABS: { id: Tab; label: string }[] = [
  { id: "overview", label: "Overview" },
  { id: "invoices", label: "Invoices" },
  { id: "statement", label: "Statement" },
  { id: "payments", label: "Payment history" },
  { id: "credits", label: "Credit notes" },
  { id: "history", label: "History" },
  { id: "tax", label: "Tax summary" },
  { id: "rates", label: "Rate card" },
  { id: "contacts", label: "Billing contacts" },
  { id: "cod", label: "COD / Connect" },
];

const PRIMARY_TABS: { id: Tab; label: string }[] = [
  { id: "overview", label: "Overview" },
  { id: "invoices", label: "Invoices" },
  { id: "rates", label: "Rate card" },
  { id: "contacts", label: "Billing contacts" },
  { id: "cod", label: "COD" },
];

const INVOICE_PANELS: { id: Tab; label: string }[] = [
  { id: "invoices", label: "Invoices" },
  { id: "statement", label: "Statement" },
  { id: "payments", label: "Payments" },
  { id: "credits", label: "Credits" },
  { id: "history", label: "History" },
  { id: "tax", label: "Tax" },
];

const INVOICE_FAMILY = new Set<Tab>(INVOICE_PANELS.map((t) => t.id));

function parseBillingTab(value: string | null): Tab {
  if (value && TABS.some((t) => t.id === value)) return value as Tab;
  return "overview";
}

export default function BillingClient() {
  const { getApiToken, orgId, isLoaded, isSignedIn } = useMerchantAuth();
  const searchParams = useSearchParams();
  const router = useRouter();
  const [tab, setTab] = useState<Tab>(() => parseBillingTab(searchParams.get("tab")));
  const [overview, setOverview] = useState<BillingOverview | null>(null);
  const [invoices, setInvoices] = useState<InvoiceRow[]>([]);
  const [statement, setStatement] = useState<StatementDetail | null>(null);
  const [payments, setPayments] = useState<PaymentRow[]>([]);
  const [credits, setCredits] = useState<CreditNoteRow[]>([]);
  const [history, setHistory] = useState<BillingHistoryRow[]>([]);
  const [contacts, setContacts] = useState<BillingContact[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    if (!isSignedIn) return;
    setLoading(true);
    setError(null);
    try {
      const token = await getApiToken();
      const [ov, inv, stmt, pay, cr, hist, ap] = await Promise.all([
        billingApi.overview(token, orgId),
        billingApi.invoices(token, orgId),
        billingApi.statementDetail(token, orgId),
        billingApi.payments(token, orgId),
        billingApi.creditNotes(token, orgId),
        billingApi.history(token, orgId),
        settingsApi.listBillingContacts(token, orgId),
      ]);
      setOverview(ov);
      setInvoices(inv);
      setStatement(stmt);
      setPayments(pay);
      setCredits(cr);
      setHistory(hist);
      setContacts(ap);
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

  useEffect(() => {
    setTab(parseBillingTab(searchParams.get("tab")));
  }, [searchParams]);

  useEffect(() => {
    if (searchParams.get("paid") === "1") {
      void load();
    }
  }, [searchParams, load]);

  function gotoTab(id: Tab) {
    setTab(id);
    router.replace(`/billing?tab=${id}`, { scroll: false });
  }

  async function download(kind: "invoices" | "statement" | "history") {
    try {
      const token = await getApiToken();
      if (kind === "invoices") await billingApi.downloadInvoicesCsv(token, orgId);
      else if (kind === "statement") await billingApi.downloadStatementCsv(token, orgId);
      else await billingApi.downloadHistoryCsv(token, orgId);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not download that file.");
    }
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
        {PRIMARY_TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => gotoTab(t.id)}
            className={`rounded-lg px-3 py-1.5 text-sm ${
              t.id === "invoices"
                ? INVOICE_FAMILY.has(tab)
                  ? "bg-secondary/10 font-semibold text-secondary"
                  : "text-muted hover:text-primary"
                : tab === t.id
                  ? "bg-secondary/10 font-semibold text-secondary"
                  : "text-muted hover:text-primary"
            }`}
          >
            {t.label}
          </button>
        ))}
      </nav>

      {INVOICE_FAMILY.has(tab) && (
        <nav className="flex flex-wrap gap-1" aria-label="Invoice records">
          {INVOICE_PANELS.map((t) => (
            <button
              key={t.id}
              type="button"
              onClick={() => gotoTab(t.id)}
              className={`rounded-lg px-2.5 py-1 text-xs ${
                tab === t.id
                  ? "bg-primary font-semibold text-white"
                  : "text-muted hover:text-primary"
              }`}
            >
              {t.label}
            </button>
          ))}
        </nav>
      )}

      {tab === "overview" && (
        <OverviewTab
          overview={overview}
          orgId={orgId}
          getToken={getApiToken}
          onPaid={() => void load()}
        />
      )}
      {tab === "invoices" && (
        <InvoicesTab
          invoices={invoices}
          orgId={orgId}
          getToken={getApiToken}
          onPaid={() => void load()}
        />
      )}
      {tab === "statement" && statement && <StatementTab statement={statement} />}
      {tab === "payments" && (
        <PaymentsTab payments={payments} stripeEnabled={overview.stripe_enabled} />
      )}
      {tab === "credits" && <CreditsTab credits={credits} />}
      {tab === "history" && <HistoryTab history={history} />}
      {tab === "tax" && <TaxTab overview={overview} />}
      {tab === "rates" && <RateCardPanel getToken={getApiToken} orgId={orgId} />}
      {tab === "contacts" && (
        <BillingContactsPanel
          contacts={contacts}
          onRefresh={load}
          getToken={getApiToken}
          orgId={orgId}
        />
      )}
      {tab === "cod" && <CodConnectPanel getToken={getApiToken} orgId={orgId} />}
    </div>
  );
}

function CodConnectPanel({
  getToken,
  orgId,
}: {
  getToken: () => Promise<string>;
  orgId?: string | null;
}) {
  const [status, setStatus] = useState<{
    cod_enabled: boolean;
    stripe_connect_account_id: string | null;
    connect_ready: boolean;
  } | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setErr(null);
    try {
      const token = await getToken();
      setStatus(await billingApi.codStatus(token, orgId ?? undefined));
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Failed to load COD status");
    }
  }, [getToken, orgId]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return (
    <div className="space-y-4 rounded-lg border border-border bg-surface p-4">
      <h2 className="text-lg font-semibold text-primary">Cash on delivery (Stripe Connect)</h2>
      <p className="text-sm text-muted">
        Connect your Stripe account, then enable COD. Drivers collect via Payment Link QR at the
        door. Retail Checkout is unchanged.
      </p>
      {err && <p className="text-sm text-danger">{err}</p>}
      {status && (
        <dl className="grid gap-2 text-sm sm:grid-cols-2">
          <div>
            <dt className="text-muted">Connect account</dt>
            <dd className="font-mono text-primary">
              {status.stripe_connect_account_id || "Not connected"}
            </dd>
          </div>
          <div>
            <dt className="text-muted">COD enabled</dt>
            <dd className="text-primary">{status.cod_enabled ? "Yes" : "No"}</dd>
          </div>
        </dl>
      )}
      <div className="flex flex-wrap gap-2">
        <Button
          type="button"
          disabled={busy}
          onClick={async () => {
            setBusy(true);
            setErr(null);
            try {
              const token = await getToken();
              const res = await billingApi.codConnect(token, orgId ?? undefined);
              if (res.url) window.location.href = res.url;
              await refresh();
            } catch (e) {
              setErr(e instanceof Error ? e.message : "Connect failed");
            } finally {
              setBusy(false);
            }
          }}
        >
          {status?.connect_ready ? "Reconnect Stripe" : "Connect Stripe"}
        </Button>
        <Button
          type="button"
          variant="secondary"
          disabled={busy || !status?.connect_ready}
          onClick={async () => {
            setBusy(true);
            setErr(null);
            try {
              const token = await getToken();
              await billingApi.codEnable(token, !status?.cod_enabled, orgId ?? undefined);
              await refresh();
            } catch (e) {
              setErr(e instanceof Error ? e.message : "Update failed");
            } finally {
              setBusy(false);
            }
          }}
        >
          {status?.cod_enabled ? "Disable COD" : "Enable COD"}
        </Button>
      </div>
    </div>
  );
}

function OverviewTab({
  overview,
  orgId,
  getToken,
  onPaid,
}: {
  overview: BillingOverview;
  orgId?: string;
  getToken: () => Promise<string>;
  onPaid?: () => void;
}) {
  const cp = overview.contract_pricing;
  const [payingAll, setPayingAll] = useState(false);
  const [payNotice, setPayNotice] = useState<string | null>(null);
  const canPayAll = overview.outstanding_invoices_cents > 0;

  async function payAll() {
    setPayingAll(true);
    setPayNotice(null);
    try {
      const token = await getToken();
      const result = await billingApi.payOutstanding(token, orgId);
      if (result.pay_url) {
        window.location.href = result.pay_url;
        return;
      }
      if (result.paid) {
        setPayNotice("All open invoices paid.");
        onPaid?.();
      }
    } catch (e) {
      setPayNotice(e instanceof Error ? e.message : "Could not start payment");
    } finally {
      setPayingAll(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-muted">
          Outstanding = open invoices + uninvoiced deliveries − credits (same number as Admin).
        </p>
        {canPayAll && (
          <Button size="sm" disabled={payingAll} onClick={() => void payAll()}>
            {payingAll
              ? "Opening…"
              : `Pay all due (${formatCents(overview.outstanding_invoices_cents)})`}
          </Button>
        )}
      </div>
      {payNotice && <p className="text-sm text-muted">{payNotice}</p>}
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
        {(overview.overdue_cents ?? 0) > 0 && (
          <Kpi label="Overdue amount" value={formatCents(overview.overdue_cents!)} />
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
        {overview.credit_limit_cents != null && overview.credit_limit_cents > 0 && (
          <Kpi
            label="Headroom"
            value={formatCents(overview.headroom_cents ?? overview.available_credit_cents ?? 0)}
          />
        )}
        <Kpi
          label="Credits applied"
          value={
            (overview.credits_applied_cents ?? overview.credit_notes_cents ?? 0) > 0
              ? `−${formatCents(overview.credits_applied_cents ?? overview.credit_notes_cents ?? 0)}`
              : formatCents(0)
          }
        />
        <Kpi
          label="Tax (period)"
          value={formatCents(
            overview.tax_summary.tax_cents,
            overview.tax_summary.currency.toUpperCase()
          )}
        />
        <Kpi
          label="Invoiced total (period)"
          value={formatCents(
            overview.tax_summary.total_cents,
            overview.tax_summary.currency.toUpperCase()
          )}
        />
      </div>

      {overview.remittance && <RemittanceCard remittance={overview.remittance} />}

      {overview.glossary && overview.glossary.length > 0 && (
        <section className="rounded-2xl border border-primary/10 bg-white p-5">
          <h2 className="font-semibold text-primary">Billing words</h2>
          <dl className="mt-3 grid gap-3 sm:grid-cols-2">
            {overview.glossary.map((row) => (
              <div key={row.term}>
                <dt className="text-sm font-medium text-primary">{row.term}</dt>
                <dd className="mt-0.5 text-sm text-muted">{row.meaning}</dd>
              </div>
            ))}
          </dl>
        </section>
      )}

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
  onPaid,
}: {
  invoices: InvoiceRow[];
  orgId?: string;
  getToken: () => Promise<string>;
  onPaid?: () => void;
}) {
  const [remindingId, setRemindingId] = useState<string | null>(null);
  const [payingId, setPayingId] = useState<string | null>(null);
  const [pdfId, setPdfId] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  async function openPdf(inv: InvoiceRow) {
    setPdfId(inv.invoice_id);
    setNotice(null);
    try {
      const token = await getToken();
      await billingApi.downloadInvoicePdf(
        token,
        inv.invoice_id,
        orgId,
        `invoice-${inv.invoice_number}.pdf`
      );
    } catch (e) {
      setNotice(e instanceof Error ? e.message : "Could not download that invoice PDF.");
    } finally {
      setPdfId(null);
    }
  }

  async function resend(invoiceId: string) {
    setRemindingId(invoiceId);
    setNotice(null);
    try {
      const token = await getToken();
      const result = await billingApi.remindInvoice(token, invoiceId, orgId);
      setNotice(`Reminder sent to ${result.email}`);
    } catch (e) {
      setNotice(e instanceof Error ? e.message : "Could not send reminder");
    } finally {
      setRemindingId(null);
    }
  }

  async function payNow(invoiceId: string) {
    setPayingId(invoiceId);
    setNotice(null);
    try {
      const token = await getToken();
      const result = await billingApi.payInvoice(token, invoiceId, orgId);
      if (result.pay_url) {
        window.location.href = result.pay_url;
        return;
      }
      if (result.paid) {
        setNotice("Invoice paid.");
        onPaid?.();
      }
    } catch (e) {
      setNotice(e instanceof Error ? e.message : "Could not start payment");
    } finally {
      setPayingId(null);
    }
  }

  if (!invoices.length) {
    return (
      <p className="text-sm text-muted">No invoices yet — net terms orders appear when invoiced.</p>
    );
  }

  return (
    <div className="space-y-2">
      {notice && <p className="text-sm text-muted">{notice}</p>}
      <div className="ops-table-scroll rounded-2xl border border-primary/10 bg-white">
        <table className="w-full min-w-[720px] text-left text-sm">
          <thead>
            <tr className="border-b border-primary/10 text-muted">
              <th className="px-4 py-3">Invoice</th>
              <th className="px-4 py-3">Order</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Amount</th>
              <th className="px-4 py-3">Due</th>
              <th className="px-4 py-3">PDF</th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody>
            {invoices.map((inv) => (
              <tr key={inv.invoice_id} className="border-b border-primary/5">
                <td className="px-4 py-3 font-mono text-xs">
                  <Link
                    href={`/billing/invoices/${inv.invoice_id}`}
                    className="text-secondary hover:underline"
                  >
                    {inv.invoice_number}
                  </Link>
                </td>
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
                  <button
                    type="button"
                    className="text-secondary hover:underline disabled:opacity-40"
                    disabled={pdfId === inv.invoice_id}
                    onClick={() => void openPdf(inv)}
                  >
                    {pdfId === inv.invoice_id ? "Preparing…" : "Download PDF"}
                  </button>
                </td>
                <td className="px-4 py-3">
                  <div className="flex flex-wrap items-center gap-3">
                    {inv.outstanding_cents > 0 && inv.status !== "paid" && (
                      <button
                        type="button"
                        className="text-xs font-semibold text-primary hover:underline disabled:opacity-40"
                        disabled={payingId === inv.invoice_id}
                        onClick={() => void payNow(inv.invoice_id)}
                      >
                        {payingId === inv.invoice_id ? "Opening…" : "Pay now"}
                      </button>
                    )}
                    {inv.outstanding_cents > 0 && inv.status !== "paid" && (
                      <button
                        type="button"
                        className="text-xs font-semibold text-secondary hover:underline disabled:opacity-40"
                        disabled={remindingId === inv.invoice_id}
                        onClick={() => void resend(inv.invoice_id)}
                      >
                        {remindingId === inv.invoice_id ? "Sending…" : "Resend"}
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
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
      <div className="ops-table-scroll rounded-2xl border border-primary/10 bg-white">
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

function RemittanceCard({
  remittance,
}: {
  remittance: NonNullable<BillingOverview["remittance"]>;
}) {
  return (
    <section className="rounded-2xl border border-primary/10 bg-white p-5">
      <h2 className="font-semibold text-primary">How to pay</h2>
      <p className="mt-2 text-sm text-muted">{remittance.instructions}</p>
      <dl className="mt-4 grid gap-3 sm:grid-cols-2 text-sm">
        <div>
          <dt className="text-muted">Pay to</dt>
          <dd className="font-medium text-primary">{remittance.payee}</dd>
        </div>
        <div>
          <dt className="text-muted">Memo / invoice numbers</dt>
          <dd className="font-mono text-xs text-primary">{remittance.memo}</dd>
        </div>
        <div>
          <dt className="text-muted">Remittance advice</dt>
          <dd className="text-primary">
            {remittance.advice_email || "Add a billing email in Settings"}
          </dd>
        </div>
        <div>
          <dt className="text-muted">Amount due now</dt>
          <dd className="font-medium text-primary">{formatCents(remittance.outstanding_cents)}</dd>
        </div>
        {remittance.credits_applied_cents > 0 && (
          <div>
            <dt className="text-muted">Credits already applied</dt>
            <dd className="text-primary">−{formatCents(remittance.credits_applied_cents)}</dd>
          </div>
        )}
      </dl>
    </section>
  );
}

function CreditsTab({ credits }: { credits: CreditNoteRow[] }) {
  if (!credits.length) {
    return (
      <p className="text-sm text-muted">
        No credit notes on file. When we issue a credit, it reduces Outstanding (credits applied).
      </p>
    );
  }
  return (
    <div className="space-y-3">
      <p className="text-sm text-muted">
        These credits are already applied to Outstanding. They reduce what you owe.
      </p>
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
    </div>
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
  const label = invoiceStatusLabel(status);
  const paid = paymentStatusLabel(status);
  const text = label !== "—" && INVOICE_KEYS.has(status) ? label : paid;
  return <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${style}`}>{text}</span>;
}

const INVOICE_KEYS = new Set([
  "none",
  "generated",
  "draft",
  "pending",
  "sent",
  "paid",
  "overdue",
  "void",
  "partial",
]);
