import { dehydrate, HydrationBoundary, QueryClient } from "@tanstack/react-query";
import EarningsClient from "@/components/earnings/EarningsClient";
import { driverServerGet } from "@/lib/server-api";

export default async function EarningsPage() {
  const client = new QueryClient();
  const [snapshot, statements] = await Promise.all([
    driverServerGet<unknown>("/v1/earnings"),
    driverServerGet<{ statements: unknown[] }>("/v1/earnings/statements"),
  ]);
  if (snapshot) client.setQueryData(["driver-earnings"], snapshot);
  if (statements) client.setQueryData(["driver-earnings-statements"], statements.statements ?? []);

  return (
    <HydrationBoundary state={dehydrate(client)}>
      <EarningsClient />
    </HydrationBoundary>
  );
}
