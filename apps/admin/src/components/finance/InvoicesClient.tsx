"use client";

import dynamic from "next/dynamic";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { formatCents } from "@porterchain/ui/utils";
import { PageSkeleton, TableSkeleton } from "@porterchain/ui/loading";
import { ListPager } from "@/components/crm/ListPager";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { exportGlCsv, financeApi, INVOICE_STATUSES, type FinanceFilters } from "@/lib/finance";
import { FinanceShell, Hero, PrimaryButton, Section, Stat } from "./FinanceShell";

const FinanceInvoicesGrid = dynamic(() => import("@/components/finance/FinanceInvoicesGrid"), {
  ssr: false,
  loading: () => <TableSkeleton rows={6} />,
});
const FinanceArSummary = dynamic(() => import("@/components/finance/FinanceArSummary"), {
  ssr: false,
});
const FinanceMerchantArPanel = dynamic(
  () => import("@/components/finance/FinanceMerchantArPanel"),
  {
    ssr: false,
    loading: () => <PageSkeleton rows={3} />,
  }
);

export default function InvoicesClient() {
  const { getApiToken, isLoaded, isSignedIn } = useAdminAuth();
  const enabled = isLoaded && (isSignedIn || process.env.NODE_ENV === "development");
  const [filters, setFilters] = useState<FinanceFilters>({});
  const [offset, setOffset] = useState(0);
  const [showCycle, setShowCycle] = useState(false);

  const dash = useQuery({
    queryKey: ["finance-dashboard"],
    enabled,
    queryFn: async () => financeApi.dashboard(await getApiToken()),
  });
  const page = useQuery({
    queryKey: ["finance-invoices", JSON.stringify(filters), offset],
    enabled,
    queryFn: async () =>
      financeApi.invoices(await getApiToken(), { ...filters, limit: 25, offset }),
  });

  async function exportGl() {
    exportGlCsv(await financeApi.exportGl(await getApiToken()));
  }

  const d = dash.data;
  const set = (patch: Partial<FinanceFilters>) => {
    setOffset(0);
    setFilters((f) => ({ ...f, ...patch }));
  };

  return (
    <FinanceShell
      title="Invoices"
      subtitle="One invoice per merchant per cycle. Numbers are sequential with no gaps."
      primary={<PrimaryButton onClick={() => void exportGl()}>Export GL (CSV)</PrimaryButton>}
    >
      {d ? (
        <Hero label="Open invoices" value={formatCents(d.outstanding_invoices_cents)}>
          <div className="grid grid-cols-2 gap-6 border-t border-primary/10 pt-5 sm:grid-cols-4">
            <Stat label="Open" value={String(d.outstanding_invoice_count)} />
            <Stat
              label="Overdue"
              value={String(d.overdue_invoices_count)}
              tone={d.overdue_invoices_count ? "bad" : "good"}
            />
            <Stat label="Paid (month)" value={formatCents(d.paid_invoices_cents)} />
            <Stat label="Tax collected" value={formatCents(d.taxes_collected_cents)} />
          </div>
        </Hero>
      ) : (
        <PageSkeleton rows={2} />
      )}

      <FinanceArSummary />

      <Section
        title="All invoices"
        aside={
          <button
            type="button"
            onClick={() => setShowCycle((v) => !v)}
            className="min-h-10 rounded-xl px-3 text-sm font-semibold text-secondary hover:bg-secondary/10"
            aria-expanded={showCycle}
          >
            {showCycle ? "Hide billing run" : "Run a billing cycle"}
          </button>
        }
      >
        {showCycle ? (
          <div className="mb-6 rounded-2xl bg-primary/[0.03] p-4">
            <FinanceMerchantArPanel />
          </div>
        ) : null}
        <div className="mb-4 flex flex-wrap gap-2">
          <input
            placeholder="Invoice #, PC code, order, merchant…"
            aria-label="Search invoices"
            value={filters.search ?? ""}
            onChange={(e) => set({ search: e.target.value || undefined })}
            className="min-h-11 min-w-0 flex-1 basis-56 rounded-xl border border-primary/15 bg-white px-3 text-sm"
          />
          <select
            aria-label="Status"
            value={filters.status ?? ""}
            onChange={(e) => set({ status: e.target.value || undefined })}
            className="min-h-11 rounded-xl border border-primary/15 bg-white px-3 text-sm"
          >
            <option value="">All statuses</option>
            {INVOICE_STATUSES.map((s) => (
              <option key={s} value={s}>
                {s.replace(/_/g, " ")}
              </option>
            ))}
          </select>
          <label className="flex min-h-11 items-center gap-2 rounded-xl border border-primary/15 px-3 text-sm text-primary">
            <input
              type="checkbox"
              checked={filters.outstanding_only ?? false}
              onChange={(e) => set({ outstanding_only: e.target.checked || undefined })}
            />
            Unpaid only
          </label>
        </div>
        {page.isLoading ? (
          <TableSkeleton rows={8} />
        ) : (
          <>
            <FinanceInvoicesGrid rows={page.data?.items ?? []} hideToolbar />
            <ListPager
              total={page.data?.total ?? 0}
              limit={page.data?.limit ?? 25}
              offset={offset}
              onPage={setOffset}
            />
          </>
        )}
      </Section>
    </FinanceShell>
  );
}
