"use client";

import { BillingContactsPanel } from "@/components/billing/BillingContactsPanel";
import { RateCardPanel } from "@/components/billing/RateCardPanel";
import Button from "@/components/ui/Button";
import { useMerchantAuth } from "@/hooks/useMerchantAuth";
import { billingApi, formatCycle, formatTerms } from "@/lib/billing";
import { settingsApi } from "@/lib/settings";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import dynamic from "next/dynamic";
import { PageSkeleton } from "@porterchain/ui/loading";

const OverviewTab = dynamic(() => import("./tabs/OverviewTab").then((m) => m.OverviewTab), {
  loading: () => <PageSkeleton rows={4} />,
});
const InvoicesTab = dynamic(() => import("./tabs/InvoicesTab").then((m) => m.InvoicesTab), {
  loading: () => <PageSkeleton rows={4} />,
});
const StatementTab = dynamic(() => import("./tabs/StatementTab").then((m) => m.StatementTab), {
  loading: () => <PageSkeleton rows={3} />,
});
const PaymentsTab = dynamic(() => import("./tabs/PaymentsTab").then((m) => m.PaymentsTab), {
  loading: () => <PageSkeleton rows={3} />,
});
const CreditsTab = dynamic(() => import("./tabs/CreditsTab").then((m) => m.CreditsTab), {
  loading: () => <PageSkeleton rows={3} />,
});
const HistoryTab = dynamic(() => import("./tabs/HistoryTab").then((m) => m.HistoryTab), {
  loading: () => <PageSkeleton rows={3} />,
});
const TaxTab = dynamic(() => import("./tabs/TaxTab").then((m) => m.TaxTab), {
  loading: () => <PageSkeleton rows={3} />,
});
const CodConnectPanel = dynamic(
  () => import("./tabs/CodConnectPanel").then((m) => m.CodConnectPanel),
  { loading: () => <PageSkeleton rows={3} /> }
);

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
  const qc = useQueryClient();
  const [tab, setTab] = useState<Tab>(() => parseBillingTab(searchParams.get("tab")));
  const [actionError, setActionError] = useState<string | null>(null);

  const enabled = Boolean(isLoaded && isSignedIn && orgId);
  const invoiceFamily = INVOICE_FAMILY.has(tab);

  const overviewQuery = useQuery({
    queryKey: ["merchant-billing", "overview", orgId],
    enabled,
    queryFn: async () => billingApi.overview(await getApiToken(), orgId),
  });

  const invoicesQuery = useQuery({
    queryKey: ["merchant-billing", "invoices", orgId],
    enabled: enabled && (tab === "invoices" || tab === "overview"),
    queryFn: async () => billingApi.invoices(await getApiToken(), orgId),
  });

  const statementQuery = useQuery({
    queryKey: ["merchant-billing", "statement", orgId],
    enabled: enabled && tab === "statement",
    queryFn: async () => billingApi.statementDetail(await getApiToken(), orgId),
  });

  const paymentsQuery = useQuery({
    queryKey: ["merchant-billing", "payments", orgId],
    enabled: enabled && tab === "payments",
    queryFn: async () => billingApi.payments(await getApiToken(), orgId),
  });

  const creditsQuery = useQuery({
    queryKey: ["merchant-billing", "credits", orgId],
    enabled: enabled && tab === "credits",
    queryFn: async () => billingApi.creditNotes(await getApiToken(), orgId),
  });

  const historyQuery = useQuery({
    queryKey: ["merchant-billing", "history", orgId],
    enabled: enabled && tab === "history",
    queryFn: async () => billingApi.history(await getApiToken(), orgId),
  });

  const contactsQuery = useQuery({
    queryKey: ["merchant-billing", "contacts", orgId],
    enabled: enabled && tab === "contacts",
    queryFn: async () => settingsApi.listBillingContacts(await getApiToken(), orgId),
  });

  useEffect(() => {
    setTab(parseBillingTab(searchParams.get("tab")));
  }, [searchParams]);

  useEffect(() => {
    if (searchParams.get("paid") === "1") {
      void qc.invalidateQueries({ queryKey: ["merchant-billing"] });
    }
  }, [searchParams, qc]);

  function gotoTab(id: Tab) {
    setTab(id);
    router.replace(`/billing?tab=${id}`, { scroll: false });
  }

  async function refreshBilling() {
    await qc.invalidateQueries({ queryKey: ["merchant-billing"] });
  }

  async function download(kind: "invoices" | "statement" | "history" | "statement-pdf") {
    try {
      const token = await getApiToken();
      if (kind === "statement-pdf") await billingApi.downloadStatementPdf(token, orgId);
      else if (kind === "invoices") await billingApi.downloadInvoicesCsv(token, orgId);
      else if (kind === "statement") await billingApi.downloadStatementCsv(token, orgId);
      else await billingApi.downloadHistoryCsv(token, orgId);
    } catch (e) {
      setActionError(e instanceof Error ? e.message : "Could not download that file.");
    }
  }

  const overview = overviewQuery.data ?? null;
  const invoices = invoicesQuery.data ?? [];
  const statement = statementQuery.data ?? null;
  const payments = paymentsQuery.data ?? [];
  const credits = creditsQuery.data ?? [];
  const history = historyQuery.data ?? [];
  const contacts = contactsQuery.data ?? [];
  const error =
    actionError ||
    (overviewQuery.error instanceof Error
      ? overviewQuery.error.message
      : overviewQuery.error
        ? String(overviewQuery.error)
        : invoiceFamily && invoicesQuery.error instanceof Error
          ? invoicesQuery.error.message
          : null);

  if (error && !overview) return <p className="text-red-600">{error}</p>;
  if (!overview) return <PageSkeleton rows={5} />;

  return (
    <div className="mx-auto max-w-5xl space-y-8">
      {error ? (
        <p className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
          {error}
        </p>
      ) : null}
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-primary">Billing</h1>
          <p className="mt-1 text-sm text-muted">
            {formatTerms(overview.payment_terms)} · {formatCycle(overview.billing_cycle)} invoice
          </p>
        </div>
        <div className="flex w-full flex-wrap items-center gap-3 sm:w-auto">
          <Button
            className="min-h-11 flex-1 sm:flex-none"
            onClick={() => void download("statement-pdf")}
          >
            Download statement (PDF)
          </Button>
          <details className="relative">
            <summary className="min-h-11 cursor-pointer list-none rounded-xl px-3 py-2.5 text-sm font-medium text-secondary hover:bg-secondary/10">
              Export CSV
            </summary>
            <div className="absolute right-0 z-10 mt-1 w-48 rounded-xl border border-primary/10 bg-white p-1 shadow-lg">
              {(
                [
                  ["invoices", "Invoices"],
                  ["statement", "Statement"],
                  ["history", "History"],
                ] as const
              ).map(([kind, label]) => (
                <button
                  key={kind}
                  type="button"
                  onClick={() => void download(kind)}
                  className="block w-full rounded-lg px-3 py-2 text-left text-sm text-primary hover:bg-primary/5"
                >
                  {label}
                </button>
              ))}
            </div>
          </details>
        </div>
      </div>

      <nav
        className="-mx-1 flex gap-1 overflow-x-auto border-b border-primary/10 px-1 pb-1"
        aria-label="Billing"
      >
        {PRIMARY_TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => gotoTab(t.id)}
            className={`shrink-0 rounded-lg px-3 py-2 text-sm ${
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

      {tab === "overview" && <OverviewTab overview={overview} />}
      {tab === "invoices" && (
        <InvoicesTab invoices={invoices} orgId={orgId} getToken={getApiToken} />
      )}
      {tab === "statement" && statement && <StatementTab statement={statement} />}
      {tab === "statement" && !statement && statementQuery.isLoading && <PageSkeleton rows={3} />}
      {tab === "payments" && <PaymentsTab payments={payments} />}
      {tab === "credits" && <CreditsTab credits={credits} />}
      {tab === "history" && <HistoryTab history={history} />}
      {tab === "tax" && <TaxTab overview={overview} />}
      {tab === "rates" && <RateCardPanel getToken={getApiToken} orgId={orgId} />}
      {tab === "contacts" && (
        <BillingContactsPanel
          contacts={contacts}
          onRefresh={refreshBilling}
          getToken={getApiToken}
          orgId={orgId}
        />
      )}
      {tab === "cod" && <CodConnectPanel getToken={getApiToken} orgId={orgId} />}
    </div>
  );
}
