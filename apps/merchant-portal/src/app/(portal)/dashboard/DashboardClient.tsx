"use client";

import { NotificationCenter } from "@/components/dashboard/NotificationCenter";
import {
  OrdersPerformanceChart,
  SpendPerformanceChart,
} from "@/components/dashboard/PerformanceChart";
import { QuickActions } from "@/components/dashboard/QuickActions";
import { RecentActivity } from "@/components/dashboard/RecentActivity";
import { RecentDeliveries } from "@/components/dashboard/RecentDeliveries";
import { StatCard } from "@/components/portal/StatCard";
import { useMerchantAuth } from "@/hooks/useMerchantAuth";
import { useMerchantRealtime } from "@/hooks/useMerchantRealtime";
import { getDashboard, type MerchantDashboard } from "@/lib/api";
import { formatCents } from "@/lib/utils";
import { useCallback, useEffect, useState } from "react";

export default function DashboardPage() {
  const { getApiToken, orgId, isLoaded, isSignedIn } = useMerchantAuth();
  const [data, setData] = useState<MerchantDashboard | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const loadDashboard = useCallback(async () => {
    const token = await getApiToken();
    return getDashboard(token, orgId);
  }, [getApiToken, orgId]);

  const refresh = useCallback(async () => {
    if (!isSignedIn) return;
    setRefreshing(true);
    try {
      const dash = await loadDashboard();
      setData(dash);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load dashboard");
    } finally {
      setRefreshing(false);
    }
  }, [isSignedIn, loadDashboard]);

  useEffect(() => {
    if (!isLoaded || !isSignedIn) return;
    let cancelled = false;
    void (async () => {
      try {
        const dash = await loadDashboard();
        if (!cancelled) {
          setData(dash);
          setError(null);
        }
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load dashboard");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [isLoaded, isSignedIn, loadDashboard]);

  useMerchantRealtime(isLoaded && isSignedIn, orgId, getApiToken, refresh);

  if (!isLoaded) return <p className="text-muted">Loading…</p>;
  if (!isSignedIn) return <p className="text-muted">Please sign in.</p>;
  if (error && !data) return <p className="text-red-600">{error}</p>;
  if (!data) return <p className="text-muted">Loading dashboard…</p>;

  const invoiceUrl =
    data.latest_invoice?.pdf_url ?? data.latest_invoice?.stripe_receipt_url ?? null;

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-primary">Executive Dashboard</h1>
          <p className="text-sm text-muted">
            Operational command center · {data.payment_terms.replace("_", " ")}
            {refreshing && <span className="ml-2 text-secondary">Updating…</span>}
          </p>
        </div>
        <p className="text-xs text-muted">Live via WebSocket + 60s refresh</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Today's Orders" value={String(data.todays_orders)} />
        <StatCard label="Orders Awaiting Pickup" value={String(data.awaiting_pickup)} />
        <StatCard label="In Transit" value={String(data.in_transit)} />
        <StatCard label="Delivered Today" value={String(data.delivered_today)} />
        <StatCard label="Monthly Orders" value={String(data.monthly_orders)} />
        <StatCard label="Monthly Spend" value={formatCents(data.monthly_spend_cents)} />
        <StatCard label="Outstanding Balance" value={formatCents(data.outstanding_balance_cents)} />
        <StatCard label="Invoices Due" value={String(data.invoices_due)} />
        <StatCard label="Open Claims" value={String(data.open_claims)} />
        <StatCard label="Open Support Tickets" value={String(data.open_support_tickets)} />
        <StatCard label="On-Time Delivery" value={`${data.on_time_percent}%`} hint="This month" />
        <StatCard
          label="Delivery Success"
          value={`${data.delivery_success_percent}%`}
          hint="This month"
        />
      </div>

      <QuickActions invoiceUrl={invoiceUrl} />

      <div className="grid gap-6 lg:grid-cols-2">
        <OrdersPerformanceChart series={data.performance_charts.daily_orders} />
        <SpendPerformanceChart series={data.performance_charts.daily_spend_cents} />
      </div>

      <div className="grid gap-6 xl:grid-cols-3">
        <div className="xl:col-span-2">
          <RecentDeliveries items={data.recent_deliveries} />
        </div>
        <NotificationCenter
          items={data.notifications}
          getToken={getApiToken}
          orgId={orgId}
          onRead={() => void refresh()}
        />
      </div>

      <RecentActivity items={data.recent_activity} />
    </div>
  );
}
