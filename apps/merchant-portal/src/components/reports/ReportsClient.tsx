"use client";

import dynamic from "next/dynamic";
import Button from "@/components/ui/Button";
import { EmptyState } from "@porterchain/ui/empty-state";
import { PageSkeleton } from "@porterchain/ui/loading";
import { useMerchantAuth } from "@/hooks/useMerchantAuth";
import { reportsApi, type ReportsOverview } from "@/lib/reports";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

type Tab = "executive" | "delivery" | "invoices" | "claims" | "saved";

const TABS: { id: Tab; label: string }[] = [
  { id: "executive", label: "Overview" },
  { id: "delivery", label: "Delivery" },
  { id: "invoices", label: "Invoices" },
  { id: "claims", label: "Claims" },
  { id: "saved", label: "Saved" },
];

const TAB_ALIASES: Record<string, Tab> = {
  executive: "executive",
  delivery: "delivery",
  orders: "delivery",
  destinations: "delivery",
  drivers: "delivery",
  vehicles: "delivery",
  invoices: "invoices",
  claims: "claims",
  saved: "saved",
};

function parseReportTab(value: string | null | undefined): Tab {
  if (value && value in TAB_ALIASES) return TAB_ALIASES[value];
  return "executive";
}

const ExecutiveTab = dynamic(() => import("./tabs/ExecutiveTab").then((m) => m.ExecutiveTab), {
  loading: () => <PageSkeleton rows={3} />,
});
const DeliverySection = dynamic(() => import("./tabs/DeliveryTab").then((m) => m.DeliverySection), {
  loading: () => <PageSkeleton rows={4} />,
});
const InvoicesTab = dynamic(() => import("./tabs/InvoicesTab").then((m) => m.InvoicesTab), {
  loading: () => <PageSkeleton rows={3} />,
});
const ClaimsTab = dynamic(() => import("./tabs/ClaimsTab").then((m) => m.ClaimsTab), {
  loading: () => <PageSkeleton rows={2} />,
});
const SavedTab = dynamic(() => import("./tabs/SavedTab").then((m) => m.SavedTab), {
  loading: () => <PageSkeleton rows={2} />,
});

export default function ReportsClient() {
  const { getApiToken, orgId, isLoaded, isSignedIn } = useMerchantAuth();
  const qc = useQueryClient();
  const [tab, setTab] = useState<Tab>("executive");
  const [exporting, setExporting] = useState<string | null>(null);
  const [exportError, setExportError] = useState<string | null>(null);

  const enabled = Boolean(isLoaded && isSignedIn && orgId);

  const overviewQuery = useQuery({
    queryKey: ["merchant-reports-overview", orgId],
    enabled,
    staleTime: 60_000,
    queryFn: async () => reportsApi.overview(await getApiToken(), orgId),
  });

  const savedQuery = useQuery({
    queryKey: ["merchant-reports-saved", orgId],
    enabled: enabled && tab === "saved",
    staleTime: 30_000,
    queryFn: async () => reportsApi.saved(await getApiToken(), orgId),
  });

  const data = overviewQuery.data ?? null;
  const saved = savedQuery.data ?? [];
  const error =
    overviewQuery.error instanceof Error
      ? overviewQuery.error.message
      : overviewQuery.error
        ? "Could not load reports"
        : null;

  const load = async () => {
    await Promise.all([
      qc.invalidateQueries({ queryKey: ["merchant-reports-overview", orgId] }),
      qc.invalidateQueries({ queryKey: ["merchant-reports-saved", orgId] }),
    ]);
  };

  const handleExport = async (reportType: string, format: "csv" | "xlsx") => {
    setExporting(`${reportType}-${format}`);
    setExportError(null);
    try {
      const token = await getApiToken();
      if (format === "csv") await reportsApi.exportCsv(token, reportType, orgId);
      else await reportsApi.exportExcel(token, reportType, orgId);
    } catch (e) {
      setExportError(e instanceof Error ? e.message : "Could not download that report.");
    } finally {
      setExporting(null);
    }
  };

  if (!isLoaded || (overviewQuery.isLoading && !data)) {
    return <PageSkeleton rows={4} />;
  }

  if (error && !data) {
    return (
      <EmptyState
        title="Reports unavailable"
        hint={error}
        action={<Button onClick={() => void load()}>Retry</Button>}
      />
    );
  }

  if (!data) return null;

  const exportTypeForTab: Record<Tab, string> = {
    executive: "delivery",
    delivery: "delivery",
    invoices: "invoices",
    claims: "claims",
    saved: "orders",
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-primary">Reports</h1>
          <p className="mt-1 text-sm text-muted">
            {data.period?.label ?? "This calendar month"}
            {data.period?.timezone ? ` · ${data.period.timezone}` : ""}. On-time is promised time vs
            delivered time (30-minute grace). A dash means there is not enough completed work to
            score.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button
            variant="outline"
            size="sm"
            disabled={!!exporting}
            onClick={() => void handleExport(exportTypeForTab[tab], "csv")}
          >
            Export CSV
          </Button>
          <Button
            variant="outline"
            size="sm"
            disabled={!!exporting}
            onClick={() => void handleExport(exportTypeForTab[tab], "xlsx")}
          >
            Export Excel
          </Button>
        </div>
      </div>

      {(error || exportError) && <p className="text-sm text-red-600">{exportError || error}</p>}

      <nav
        className="ops-tab-rail rounded-2xl border border-primary/10 bg-white"
        aria-label="Reports"
      >
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setTab(t.id)}
            className={`min-h-10 shrink-0 rounded-xl px-3 py-1.5 text-sm font-medium whitespace-nowrap transition ${
              tab === t.id ? "bg-primary text-white" : "text-muted hover:bg-primary/5"
            }`}
          >
            {t.label}
          </button>
        ))}
      </nav>

      {tab === "executive" && <ExecutiveTab data={data.executive} />}
      {tab === "delivery" && (
        <DeliverySection
          delivery={data.delivery_performance}
          orderVolume={data.order_volume}
          destinations={data.top_destinations.destinations}
        />
      )}
      {tab === "invoices" && <InvoicesTab data={data.invoice_reports} />}
      {tab === "claims" && <ClaimsTab data={data.claims_summary} />}
      {tab === "saved" && (
        <SavedTab
          saved={saved}
          onOpen={(reportType) => setTab(parseReportTab(reportType))}
          onRefresh={load}
          getToken={getApiToken}
          orgId={orgId}
        />
      )}
    </div>
  );
}
