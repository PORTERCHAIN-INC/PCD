import { Suspense } from "react";
import { dehydrate, HydrationBoundary, QueryClient } from "@tanstack/react-query";
import { PageSkeleton, RouteLoading } from "@porterchain/ui/loading";
import BillingClient from "@/components/billing/BillingClient";
import { merchantOrgId, merchantServerFetch } from "@/lib/server-api";

export default async function BillingPage() {
  const orgId = await merchantOrgId();
  const client = new QueryClient();
  if (orgId) {
    const [overview, invoices] = await Promise.all([
      merchantServerFetch<unknown>("/v1/merchant/billing/overview", orgId),
      merchantServerFetch<unknown>("/v1/merchant/billing/invoices", orgId),
    ]);
    if (overview) client.setQueryData(["merchant-billing", "overview", orgId], overview);
    if (invoices) client.setQueryData(["merchant-billing", "invoices", orgId], invoices);
  }

  return (
    <HydrationBoundary state={dehydrate(client)}>
      <Suspense
        fallback={
          <RouteLoading label="Loading billing">
            <PageSkeleton rows={4} />
          </RouteLoading>
        }
      >
        <BillingClient />
      </Suspense>
    </HydrationBoundary>
  );
}
