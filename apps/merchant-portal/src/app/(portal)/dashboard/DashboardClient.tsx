"use client";

import { NotificationCenter } from "@/components/dashboard/NotificationCenter";
import { MerchantDashboardGraphics } from "@/components/dashboard/MerchantDashboardGraphics";
import { QuickActions } from "@/components/dashboard/QuickActions";
import { RecentActivity } from "@/components/dashboard/RecentActivity";
import { RecentDeliveries } from "@/components/dashboard/RecentDeliveries";
import CompanyCompletenessBanner from "@/components/onboarding/CompanyCompletenessBanner";
import { useMerchantAuth } from "@/hooks/useMerchantAuth";
import { useMerchantRealtime } from "@/hooks/useMerchantRealtime";
import { getDashboard } from "@/lib/api";
import { merchantPortalJob } from "@/lib/merchant-nav";
import { PageSkeleton } from "@porterchain/ui/loading";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback } from "react";

export default function DashboardPage() {
  const { getApiToken, orgId, isLoaded, isSignedIn, modules } = useMerchantAuth();
  const job = merchantPortalJob(modules);
  const qc = useQueryClient();
  const enabled = Boolean(isLoaded && isSignedIn && orgId);

  const { data, error, isLoading, isFetching, refetch } = useQuery({
    queryKey: ["merchant-dashboard", orgId ?? null],
    enabled,
    queryFn: async () => getDashboard(await getApiToken(), orgId),
  });

  const refresh = useCallback(() => {
    void qc.invalidateQueries({ queryKey: ["merchant-dashboard", orgId ?? null] });
  }, [orgId, qc]);

  useMerchantRealtime(enabled, orgId, getApiToken, refresh);

  if (error && !data) {
    return (
      <p className="text-red-600">
        {error instanceof Error ? error.message : "Failed to load dashboard"}
      </p>
    );
  }
  if (!data && (isLoading || !isLoaded || !isSignedIn)) {
    return <PageSkeleton rows={5} />;
  }
  if (!data) return null;

  const invoiceUrl =
    data.latest_invoice?.pdf_url ?? data.latest_invoice?.stripe_receipt_url ?? null;
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

      <MerchantDashboardGraphics data={data} job={job} />

      <QuickActions invoiceUrl={invoiceUrl} />

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
