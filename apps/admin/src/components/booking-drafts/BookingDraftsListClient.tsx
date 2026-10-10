"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { PageSkeleton } from "@porterchain/ui/loading";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useSearchParams } from "next/navigation";
import { RefreshCw, SlidersHorizontal } from "lucide-react";
import { formatCents } from "@porterchain/ui/utils";
import { DateRangeField } from "@porterchain/ui/date-fields";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import BookingDraftsGrid from "@/components/booking-drafts/BookingDraftsGrid";
import { Badge, Button } from "@/components/crm/primitives";
import { SavedPresetsControl } from "@/components/crm/SavedPresetsControl";
import { bookingDraftsApi, DRAFT_STATES, type DraftFilters } from "@/lib/booking-drafts";
import AdminPage from "@/components/layout/AdminPage";
import { useShowMore } from "@/components/layout/ShowMore";

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
  const [filtersOpen, setFiltersOpen] = useState(false);

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

  const draftPage = useShowMore(rows, 25);
  const advanced = [
    filters.merchant_id,
    filters.booking_type,
    filters.payment_status,
    filters.date_from,
    filters.date_to,
    filters.state,
  ].filter(Boolean).length;
  const quick = filters.abandoned_only ? "abandoned" : filters.expired_only ? "expired" : "all";
  const setQuick = (q: "all" | "abandoned" | "expired") =>
    setFilters((f) => ({
      ...f,
      abandoned_only: q === "abandoned" || undefined,
      expired_only: q === "expired" || undefined,
    }));
  const field = "min-h-10 rounded-xl border border-primary/10 bg-white px-3 text-sm";

  return (
    <AdminPage>
      <header className="flex flex-wrap items-center gap-3">
        <div className="min-w-0 flex-1">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-secondary">Sales</p>
          <h1 className="text-2xl font-bold text-primary">Booking drafts</h1>
        </div>
        <SavedPresetsControl
          storageKey={FILTERS_KEY}
          value={filters}
          onLoad={setFilters}
          label="Presets"
        />
        <Button variant="outline" onClick={() => void refetch()} aria-label="Refresh">
          <RefreshCw className="h-4 w-4" />
        </Button>
      </header>

      {analytics && (
        <section
          className="rounded-2xl p-4 text-white"
          style={{ backgroundColor: "var(--primary)" }}
          aria-label="Draft metrics"
        >
          <div className="flex gap-6 overflow-x-auto">
            <Metric label="Conversion" value={`${analytics.conversion_rate_percent}%`} />
            <Metric
              label="Abandoned now"
              value={String(analytics.abandoned_now)}
              alert={analytics.abandoned_now > 0}
            />
            <Metric label="Active" value={String(analytics.active_drafts)} />
            <Metric label="Paid" value={`${analytics.payment_success_rate_percent}%`} />
            <Metric label="Revenue lost" value={formatCents(analytics.revenue_lost_cents)} />
            {showMoreMetrics && (
              <>
                <Metric label="Avg completion" value={`${analytics.avg_completion_minutes}m`} />
                <Metric label="Abandonment" value={`${analytics.abandonment_rate_percent}%`} />
                <Metric label="Recovered" value={`${analytics.recovery_rate_percent}%`} />
                {analytics.most_common_failure_step ? (
                  <Metric label="Top failure" value={analytics.most_common_failure_step} />
                ) : null}
              </>
            )}
            <button
              type="button"
              className="shrink-0 self-end text-xs font-semibold text-white/70 hover:text-white"
              onClick={() => setShowMoreMetrics((v) => !v)}
            >
              {showMoreMetrics ? "Less" : "More"}
            </button>
          </div>
        </section>
      )}

      <section className="rounded-2xl border border-primary/10 bg-white p-3 sm:p-4">
        <div className="flex flex-wrap items-center gap-2">
          <input
            type="search"
            placeholder="Search draft, session, quote…"
            value={filters.search ?? ""}
            onChange={(e) => setFilters((f) => ({ ...f, search: e.target.value || undefined }))}
            className={`${field} min-w-0 flex-1 basis-56`}
          />
          <div
            className="flex rounded-xl border border-primary/10 p-0.5"
            role="group"
            aria-label="Show"
          >
            {(["all", "abandoned", "expired"] as const).map((q) => (
              <button
                key={q}
                type="button"
                aria-pressed={quick === q}
                onClick={() => setQuick(q)}
                className={
                  "min-h-9 rounded-lg px-3 text-sm font-medium capitalize " +
                  (quick === q ? "bg-primary text-white" : "text-primary/70")
                }
              >
                {q}
              </button>
            ))}
          </div>
          <button
            type="button"
            aria-expanded={filtersOpen}
            onClick={() => setFiltersOpen((v) => !v)}
            className={`${field} inline-flex items-center gap-2 font-medium text-primary`}
          >
            <SlidersHorizontal className="h-4 w-4" />
            Filters
            {advanced > 0 && (
              <span className="rounded-full bg-secondary px-1.5 text-xs font-bold text-white">
                {advanced}
              </span>
            )}
          </button>
        </div>

        {filtersOpen && (
          <div
            className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-4"
            data-testid="draft-filters"
          >
            <select
              value={filters.state ?? ""}
              onChange={(e) => setFilters((f) => ({ ...f, state: e.target.value || undefined }))}
              className={field}
              aria-label="Status"
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
              className={field}
              aria-label="Type"
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
              className={field}
              aria-label="Payment status"
            >
              <option value="">Any payment</option>
              <option value="PENDING">Pending</option>
              <option value="PROCESSING">Processing</option>
              <option value="SUCCEEDED">Succeeded</option>
              <option value="FAILED">Failed</option>
            </select>
            <input
              type="text"
              placeholder="Merchant id"
              value={filters.merchant_id ?? ""}
              onChange={(e) =>
                setFilters((f) => ({ ...f, merchant_id: e.target.value.trim() || undefined }))
              }
              className={field}
              aria-label="Merchant id"
            />
            <DateRangeField
              className="sm:col-span-2"
              from={filters.date_from ?? ""}
              to={filters.date_to ?? ""}
              onFromChange={(value) => setFilters((f) => ({ ...f, date_from: value || undefined }))}
              onToChange={(value) => setFilters((f) => ({ ...f, date_to: value || undefined }))}
            />
            {advanced + (filters.search ? 1 : 0) + (quick !== "all" ? 1 : 0) > 0 && (
              <button
                type="button"
                className="min-h-10 text-left text-sm font-medium text-secondary hover:underline"
                onClick={() => setFilters({})}
              >
                Clear all filters
              </button>
            )}
          </div>
        )}

        {selected.length > 0 && (
          <div className="mt-3 flex flex-wrap items-center gap-2 rounded-xl bg-secondary/5 px-3 py-2">
            <Badge tone="blue">{selected.length} selected</Badge>
            <Button variant="outline" disabled={bulkLoading} onClick={() => void runBulk("extend")}>
              Extend
            </Button>
            <Button variant="outline" disabled={bulkLoading} onClick={() => void runBulk("cancel")}>
              Cancel
            </Button>
            <Button variant="outline" disabled={bulkLoading} onClick={() => void runBulk("expire")}>
              Expire
            </Button>
          </div>
        )}

        <div className="mt-3">
          {isLoading ? (
            <div className="flex justify-center py-12">
              <PageSkeleton rows={3} />
            </div>
          ) : (
            <>
              <BookingDraftsGrid
                rows={draftPage.visible}
                selected={selected}
                onSelect={setSelected}
              />
              {draftPage.more}
            </>
          )}
        </div>
      </section>
    </AdminPage>
  );
}

function Metric({ label, value, alert }: { label: string; value: string; alert?: boolean }) {
  return (
    <div className="min-w-[96px] shrink-0">
      <p className="text-[11px] font-semibold uppercase tracking-wide text-white/60">{label}</p>
      <p className={"text-xl font-bold tabular-nums " + (alert ? "text-amber-300" : "text-white")}>
        {value}
      </p>
    </div>
  );
}
