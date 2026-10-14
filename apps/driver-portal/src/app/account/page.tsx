import { dehydrate, HydrationBoundary, QueryClient } from "@tanstack/react-query";
import AccountClient from "@/components/account/AccountClient";
import { driverServerGet } from "@/lib/server-api";
import type { DriverAppSettings, DriverMeProfile } from "@/lib/api";

export const metadata = { title: "Account · Porterchain Driver" };

/** Server-prefetched so the page paints with data; the client refreshes quietly. */
export default async function AccountPage() {
  const client = new QueryClient();
  const [profile, settings] = await Promise.all([
    driverServerGet<DriverMeProfile>("/v1/me/profile"),
    driverServerGet<{ settings: DriverAppSettings }>("/v1/settings"),
  ]);
  if (profile) client.setQueryData(["driver-me-profile"], profile);
  if (settings) client.setQueryData(["driver-app-settings"], settings.settings);
  return (
    <HydrationBoundary state={dehydrate(client)}>
      <AccountClient version={process.env.NEXT_PUBLIC_APP_VERSION ?? "0.1.0"} />
    </HydrationBoundary>
  );
}
