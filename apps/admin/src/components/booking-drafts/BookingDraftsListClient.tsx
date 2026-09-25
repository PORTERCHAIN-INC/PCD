"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useSearchParams } from "next/navigation";
import { AlertTriangle, BarChart3, RefreshCw } from "lucide-react";
import { formatCents } from "@porterchain/ui/utils";
import { DateRangeField } from "@porterchain/ui/date-fields";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import BookingDraftsGrid from "@/components/booking-drafts/BookingDraftsGrid";
import { Badge, Button, Spinner } from "@/components/crm/primitives";
import { bookingDraftsApi, DRAFT_STATES, type DraftFilters } from "@/lib/booking-drafts";
import AdminPage from "@/components/layout/AdminPage";

const FILTERS_KEY = "porterchain.booking-drafts.saved-filters";

export default function BookingDraftsListClient() {
  const { getApiToken, isLoaded, isSignedIn } = useAdminAuth();
  const qc = useQueryClient();
  const searchParams = useSearchParams();
  const [filters, setFilters] = useState<DraftFilters>(() => {
    const merchantId = searchParams.get("merchant_id");
    return merchantId ? { merchant_id: merchantId } : {};
  });
  const [selected, setSelected] = useState<string[]>([]);
  const [bulkLoading, setBulkLoading] = useState(false);
  const [showMoreMetrics, setShowMoreMetrics] = useState(false);

  useEffect(() => {
    const merchantId = searchParams.get("merchant_id");
    if (!merchantId) return;
    setFilters((f) => (f.merchant_id === merchantId ? f : { ...f, merchant_id: merchantId }));
  }, [searchParams]);

  const filterKey = useMemo(() => JSON.stringify(filters), [filters]);

  const {
    data: rows = [],
    isLoading,
    refetch,
  } = useQuery({
    queryKey: ["booking-drafts", filterKey],
    enabled: isLoaded && (isSignedIn || process.env.NODE_ENV === "development"),
    queryFn: async () => {
      const token = await getApiToken();
      return bookingDraftsApi.list(token, filters);
    },
  });

  const { data: analytics } = useQuery({
    queryKey: ["booking-drafts-analytics"],
    enabled: isLoaded && (isSignedIn || process.env.NODE_ENV === "development"),
    queryFn: async () => {
      const token = await getApiToken();
      return bookingDraftsApi.analytics(token);
    },
  });

  const runBulk = useCallback(
    async (action: string) => {
      if (!selected.length) return;
      setBulkLoading(true);
      try {
        const token = await getApiToken();
        await bookingDraftsApi.bulk(token, selected, action);
        setSelected([]);
        await qc.invalidateQueries({ queryKey: ["booking-drafts"] });
      } finally {
        setBulkLoading(false);
      }
    },
    [selected, getApiToken, qc]
  );

  function saveFilters() {
    const name = prompt("Filter preset name");
    if (!name) return;
    const saved = JSON.parse(localStorage.getItem(FILTERS_KEY) || "{}") as Record<
      string,
      DraftFilters
    >;
    saved[name] = filters;
    localStorage.setItem(FILTERS_KEY, JSON.stringify(saved));
  }

  function loadFilters() {
    const saved = JSON.parse(localStorage.getItem(FILTERS_KEY) || "{}") as Record<
      string,
      DraftFilters
    >;
    const names = Object.keys(saved);
    if (!names.length) return alert("No saved filters");
    const name = prompt(`Load filter:\n${names.join("\n")}`);
    if (name && saved[name]) setFilters(saved[name]);
  }

  return (
    <AdminPage>
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-primary">Booking Drafts</h1>
          <p className="text-sm text-muted">
            Recover abandoned checkouts — survives refresh, auth, and device changes
          </p>
        </div>
        <Button variant="outline" onClick={() => void refetch()}>
          <RefreshCw className="h-4 w-4" />
          Refresh
        </Button>
      </div>

      {analytics && (
        <div className="space-y-2">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
            <StatCard
              icon={BarChart3}
              label="Conversion"
              value={`${analytics.conversion_rate_percent}%`}
            />
            <StatCard
              icon={AlertTriangle}
              label="Abandoned now"
              value={String(analytics.abandoned_now)}
              alert={analytics.abandoned_now > 0}
            />
            <StatCard label="Active drafts" value={String(analytics.active_drafts)} />
            <StatCard
              label="Payment success"
              value={`${analytics.payment_success_rate_percent}%`}
            />
            <StatCard label="Revenue lost" value={formatCents(analytics.revenue_lost_cents)} />
          </div>
          <button
            type="button"
            className="text-xs font-medium text-secondary hover:underline"
            onClick={() => setShowMoreMetrics((v) => !v)}
          >
            {showMoreMetrics ? "Hide metrics" : "More metrics"}
          </button>
          {showMoreMetrics ? (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              <StatCard label="Avg completion" value={`${analytics.avg_completion_minutes}m`} />
              <StatCard label="Abandonment" value={`${analytics.abandonment_rate_percent}%`} />
              <StatCard label="Recovery rate" value={`${analytics.recovery_rate_percent}%`} />
              {analytics.most_common_failure_step ? (
                <StatCard label="Top failure step" value={analytics.most_common_failure_step} />
              ) : null}
            </div>
          ) : null}
        </div>
      )}

      <div className="rounded-2xl border border-primary/10 bg-white p-4">
        <div className="mb-4 flex flex-wrap gap-2">
          <input
            type="search"
            placeholder="Search draft, session, quote…"
            value={filters.search ?? ""}
            onChange={(e) => setFilters((f) => ({ ...f, search: e.target.value || undefined }))}
            className="min-w-[200px] flex-1 rounded-xl border border-primary/10 px-3 py-2 text-sm"
          />
          <input
            type="text"
            placeholder="Merchant id"
            value={filters.merchant_id ?? ""}
            onChange={(e) =>
              setFilters((f) => ({ ...f, merchant_id: e.target.value.trim() || undefined }))
            }
            className="min-w-[180px] rounded-xl border border-primary/10 px-3 py-2 text-sm"
          />
          {filters.merchant_id ? (
            <button
              type="button"
              className="rounded-xl border border-primary/10 px-3 py-2 text-sm text-secondary hover:bg-gray-bg"
              onClick={() => setFilters((f) => ({ ...f, merchant_id: undefined }))}
            >
              Clear merchant
            </button>
          ) : null}
          <select
            value={filters.state ?? ""}
            onChange={(e) => setFilters((f) => ({ ...f, state: e.target.value || undefined }))}
            className="rounded-xl border border-primary/10 px-3 py-2 text-sm"
          >
            <option value="">All statuses</option>
            {DRAFT_STATES.map((s) => (
              <option key={s} value={s}>
                {s.replace(/_/g, " ")}
              </option>
            ))}
          </select>
          <select
            value={filters.booking_type ?? ""}
            onChange={(e) =>
              setFilters((f) => ({ ...f, booking_type: e.target.value || undefined }))
            }
            className="rounded-xl border border-primary/10 px-3 py-2 text-sm"
          >
            <option value="">All types</option>
            <option value="individual">Individual</option>
            <option value="merchant">Merchant</option>
          </select>
          <select
            value={filters.payment_status ?? ""}
            onChange={(e) =>
              setFilters((f) => ({ ...f, payment_status: e.target.value || undefined }))
            }
            className="rounded-xl border border-primary/10 px-3 py-2 text-sm"
          >
            <option value="">Payment status</option>
            <option value="PENDING">Pending</option>
            <option value="PROCESSING">Processing</option>
            <option value="SUCCEEDED">Succeeded</option>
            <option value="FAILED">Failed</option>
          </select>
          <DateRangeField
            className="w-full max-w-md"
            from={filters.date_from ?? ""}
            to={filters.date_to ?? ""}
            onFromChange={(value) => setFilters((f) => ({ ...f, date_from: value || undefined }))}
            onToChange={(value) => setFilters((f) => ({ ...f, date_to: value || undefined }))}
          />
          <label className="flex items-center gap-2 rounded-xl border border-primary/10 px-3 py-2 text-sm">
            <input
              type="checkbox"
              checked={!!filters.abandoned_only}
              onChange={(e) =>
                setFilters((f) => ({ ...f, abandoned_only: e.target.checked || undefined }))
              }
            />
            Abandoned
          </label>
          <label className="flex items-center gap-2 rounded-xl border border-primary/10 px-3 py-2 text-sm">
            <input
              type="checkbox"
              checked={!!filters.expired_only}
              onChange={(e) =>
                setFilters((f) => ({ ...f, expired_only: e.target.checked || undefined }))
              }
            />
            Expired
          </label>
          <Button variant="outline" onClick={saveFilters}>
            Save filters
          </Button>
          <Button variant="outline" onClick={loadFilters}>
            Load filters
          </Button>
        </div>

        {selected.length > 0 && (
          <div className="mb-3 flex flex-wrap items-center gap-2 rounded-xl bg-secondary/5 px-3 py-2">
            <Badge tone="blue">{selected.length} selected</Badge>
            <Button variant="outline" disabled={bulkLoading} onClick={() => void runBulk("extend")}>
              Bulk extend
            </Button>
            <Button variant="outline" disabled={bulkLoading} onClick={() => void runBulk("cancel")}>
              Bulk cancel
            </Button>
            <Button variant="outline" disabled={bulkLoading} onClick={() => void runBulk("expire")}>
              Bulk expire
            </Button>
          </div>
        )}

        {isLoading ? (
          <div className="flex justify-center py-12">
            <Spinner />
          </div>
        ) : (
          <BookingDraftsGrid rows={rows} selected={selected} onSelect={setSelected} />
        )}
      </div>
    </AdminPage>
  );
}

function StatCard({
  label,
  value,
  icon: Icon,
  alert,
}: {
  label: string;
  value: string;
  icon?: React.ComponentType<{ className?: string }>;
  alert?: boolean;
}) {
  return (
    <div
      className={
        "rounded-xl border border-primary/10 bg-white px-4 py-3 shadow-sm" +
        (alert ? " border-amber-200 bg-amber-50/50" : "")
      }
    >
      <div className="flex items-center gap-2 text-xs text-muted">
        {Icon && <Icon className="h-3.5 w-3.5" />}
        {label}
      </div>
      <p className="mt-1 text-lg font-bold text-primary">{value}</p>
    </div>
  );
}
