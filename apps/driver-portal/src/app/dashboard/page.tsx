import { dehydrate, HydrationBoundary, QueryClient } from "@tanstack/react-query";
import DashboardClient from "@/components/dashboard/DashboardClient";
import { loadDriverWorkspace } from "@/lib/server-api";

export default async function DashboardPage() {
  const client = new QueryClient();
  const workspace = await loadDriverWorkspace();
  if (workspace) {
    client.setQueryData(["driver-workspace"], workspace);
  }

  return (
    <HydrationBoundary state={dehydrate(client)}>
      <DashboardClient />
    </HydrationBoundary>
  );
}
