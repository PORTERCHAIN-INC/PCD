import { dehydrate, HydrationBoundary, QueryClient } from "@tanstack/react-query";
import WalletClient from "./wallet-client";
import { driverServerGet } from "@/lib/server-api";

export default async function WalletPage() {
  const client = new QueryClient();
  const wallet = await driverServerGet<unknown>("/v1/wallet");
  if (wallet) client.setQueryData(["driver-wallet"], wallet);

  return (
    <HydrationBoundary state={dehydrate(client)}>
      <WalletClient />
    </HydrationBoundary>
  );
}
