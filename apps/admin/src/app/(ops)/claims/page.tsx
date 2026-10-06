import { dehydrate, HydrationBoundary, QueryClient } from "@tanstack/react-query";
import ClaimsListClient from "@/components/claims/ClaimsListClient";
import { adminServerFetch } from "@/lib/server-api";

export default async function ClaimsPage() {
  const client = new QueryClient();
  const [rows, dashboard] = await Promise.all([
    adminServerFetch<unknown>("/v1/admin/claims"),
    adminServerFetch<unknown>("/v1/admin/claims/dashboard"),
  ]);
  if (rows) client.setQueryData(["claims", "{}"], rows);
  if (dashboard) client.setQueryData(["claims-dashboard"], dashboard);

  return (
    <HydrationBoundary state={dehydrate(client)}>
      <ClaimsListClient />
    </HydrationBoundary>
  );
}
