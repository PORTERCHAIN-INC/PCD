"use client";

import { NotificationCenter } from "@/components/dashboard/NotificationCenter";
import {
  OrdersPerformanceChart,
  SpendPerformanceChart,
} from "@/components/dashboard/PerformanceChart";
import { QuickActions } from "@/components/dashboard/QuickActions";
import { RecentActivity } from "@/components/dashboard/RecentActivity";
import { RecentDeliveries } from "@/components/dashboard/RecentDeliveries";
import CompanyCompletenessBanner from "@/components/onboarding/CompanyCompletenessBanner";
import { StatCard } from "@/components/portal/StatCard";
import { useMerchantAuth } from "@/hooks/useMerchantAuth";
import { useMerchantRealtime } from "@/hooks/useMerchantRealtime";
import { getDashboard } from "@/lib/api";
import { merchantPortalJob } from "@/lib/merchant-nav";
import { formatPercent } from "@/lib/reports";
import { formatCents } from "@/lib/utils";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback } from "react";

export default function DashboardPage() {
  const { getApiToken, orgId, isLoaded, isSignedIn, modules } = useMerchantAuth();
  const job = merchantPortalJob(modules);
  const qc = useQueryClient();
  const enabled = Boolean(isLoaded && isSignedIn && orgId);

  const { data, error, isLoading, isFetching, refetch } = useQuery({
    queryKey: ["merchant-dashboard", orgId],
    enabled,
    queryFn: async () => getDashboard(await getApiToken(), orgId),
  });

  const refresh = useCallback(() => {
    void qc.invalidateQueries({ queryKey: ["merchant-dashboard", orgId] });
  }, [orgId, qc]);

  useMerchantRealtime(enabled, orgId, getApiToken, refresh);

  if (!isLoaded) return <p className="text-muted">Loading…</p>;
  if (!isSignedIn) return <p className="text-muted">Please sign in.</p>;
  if (error && !data) {
    return (
      <p className="text-red-600">
        {error instanceof Error ? error.message : "Failed to load dashboard"}
      </p>
    );
  }
  if (isLoading || !data) return <p className="text-muted">Loading dashboard…</p>;

  const invoiceUrl =
    data.latest_invoice?.pdf_url ?? data.latest_invoice?.stripe_receipt_url ?? null;
  const showOps = job === "dispatcher" || job === "owner";
  const showFinance = job === "accounting" || job === "owner";
  const homeCopy =
    job === "dispatcher"
      ? "Today’s orders and what’s on the road"
      : job === "accounting"
        ? "What’s outstanding"
        : job === "viewer"
          ? "Track in-transit shipments"
          : "Today’s orders and what’s outstanding";

  return (
    <div className="space-y-8">
      <CompanyCompletenessBanner completeness={data.completeness} />
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="min-w-0">
          <h1 className="text-xl font-bold text-primary sm:text-2xl">Home</h1>
          <p className="text-sm text-muted">
            {homeCopy}
            {showFinance && data.payment_terms
              ? ` · ${data.payment_terms.replaceAll("_", " ")}`
              : ""}
            {isFetching && !isLoading && <span className="ml-2 text-secondary">Updating…</span>}
          </p>
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {showOps || job === "viewer" ? (
          <StatCard label="Today's Orders" value={String(data.todays_orders)} />
        ) : null}
        {showOps ? (
          <StatCard label="Orders Awaiting Pickup" value={String(data.awaiting_pickup)} />
        ) : null}
        {(showOps || job === "viewer") && (
          <StatCard label="In Transit" value={String(data.in_transit)} />
        )}
        {showOps || job === "viewer" ? (
          <StatCard label="Delivered Today" value={String(data.delivered_today)} />
        ) : null}
        {showOps ? <StatCard label="Monthly Orders" value={String(data.monthly_orders)} /> : null}
        {showFinance ? (
          <StatCard label="Monthly Spend" value={formatCents(data.monthly_spend_cents)} />
        ) : null}
        {showFinance ? (
          <StatCard
            label="Outstanding Balance"
            value={formatCents(data.outstanding_balance_cents)}
          />
        ) : null}
        {showFinance ? <StatCard label="Invoices Due" value={String(data.invoices_due)} /> : null}
        {showOps ? <StatCard label="Open Claims" value={String(data.open_claims)} /> : null}
        {job !== "viewer" ? (
          <StatCard label="Open Support Tickets" value={String(data.open_support_tickets)} />
        ) : null}
        {showOps ? (
          <StatCard
            label="On-time"
            value={formatPercent(data.on_time_percent)}
            hint="Promised vs delivered this month"
          />
        ) : null}
        {showOps ? (
          <StatCard
            label="Delivered of bookings"
            value={formatPercent(data.delivery_success_percent)}
            hint="This calendar month"
          />
        ) : null}
      </div>

      <QuickActions invoiceUrl={invoiceUrl} />

      <div className="grid gap-6 lg:grid-cols-2">
        {showOps || job === "viewer" ? (
          <OrdersPerformanceChart series={data.performance_charts.daily_orders} />
        ) : null}
        {showFinance ? (
          <SpendPerformanceChart series={data.performance_charts.daily_spend_cents} />
        ) : null}
      </div>

      <div className="grid gap-6 xl:grid-cols-3">
        <div className="xl:col-span-2">
          <RecentDeliveries items={data.recent_deliveries} />
        </div>
        <NotificationCenter
          items={data.notifications}
          getToken={getApiToken}
          orgId={orgId}
          onRead={() => void refetch()}
        />
      </div>

      <RecentActivity items={data.recent_activity} />
    </div>
  );
}
