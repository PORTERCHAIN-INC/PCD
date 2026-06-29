"use client";

import { StatCard } from "@/components/portal/StatCard";
import { useMerchantAuth } from "@/hooks/useMerchantAuth";
import { getDashboard, type MerchantDashboard } from "@/lib/api";
import { formatCents } from "@/lib/utils";
import Link from "next/link";
import { useEffect, useState } from "react";
import Button from "@/components/ui/Button";

export default function DashboardPage() {
  const { getApiToken, orgId, isLoaded, isSignedIn } = useMerchantAuth();
  const [data, setData] = useState<MerchantDashboard | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isLoaded || !isSignedIn) return;
    let cancelled = false;
    void (async () => {
      try {
        const token = await getApiToken();
        const dash = await getDashboard(token, orgId);
        if (!cancelled) setData(dash);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load dashboard");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [getApiToken, orgId, isLoaded, isSignedIn]);

  if (!isLoaded) return <p className="text-muted">Loading…</p>;
  if (!isSignedIn) return <p className="text-muted">Please sign in.</p>;
  if (error) return <p className="text-red-600">{error}</p>;
  if (!data) return <p className="text-muted">Loading dashboard…</p>;

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-primary">Dashboard</h1>
          <p className="text-sm text-muted">Today&apos;s operations at a glance</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link href="/book">
            <Button size="sm">Book Delivery</Button>
          </Link>
          <Link href="/bulk">
            <Button size="sm" variant="outline">
              Upload CSV
            </Button>
          </Link>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Today's Orders" value={String(data.todays_orders)} />
        <StatCard label="In Transit" value={String(data.in_transit)} />
        <StatCard label="Delivered Today" value={String(data.delivered_today)} />
        <StatCard label="Pending Dispatch" value={String(data.pending_dispatch)} />
        <StatCard label="Outstanding Invoices" value={formatCents(data.outstanding_invoices_cents)} />
        <StatCard label="Account Balance" value={formatCents(data.account_balance_cents)} />
        <StatCard label="Monthly Spend" value={formatCents(data.monthly_spend_cents)} />
        <StatCard label="On-Time Delivery" value={`${data.on_time_percent}%`} />
      </div>

      <section className="rounded-2xl border border-primary/10 bg-white p-6">
        <h2 className="text-lg font-semibold text-primary">Quick Actions</h2>
        <div className="mt-4 flex flex-wrap gap-3">
          <Link href="/book" className="text-sm font-medium text-secondary hover:underline">
            Book Delivery
          </Link>
          <Link href="/bulk" className="text-sm font-medium text-secondary hover:underline">
            Upload CSV
          </Link>
          <Link href="/track" className="text-sm font-medium text-secondary hover:underline">
            Track Shipment
          </Link>
          <Link href="/billing" className="text-sm font-medium text-secondary hover:underline">
            View Invoices
          </Link>
        </div>
      </section>
    </div>
  );
}
