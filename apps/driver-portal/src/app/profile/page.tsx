import { dehydrate, HydrationBoundary, QueryClient } from "@tanstack/react-query";
import DriverProfileClient from "@/components/profile/DriverProfileClient";
import { driverServerGet } from "@/lib/server-api";

export default async function ProfilePage() {
  const client = new QueryClient();
  const [snap, identity, background, abstract] = await Promise.all([
    driverServerGet<Record<string, unknown> | null>("/v1/profile"),
    driverServerGet<{ enabled?: boolean }>("/v1/verification/identity"),
    driverServerGet<{ enabled?: boolean }>("/v1/verification/background"),
    driverServerGet<{ enabled?: boolean }>("/v1/verification/abstract"),
  ]);
  if (snap) {
    client.setQueryData(["driver-profile"], {
      data: snap,
      features: {
        identity: Boolean(identity?.enabled),
        background: Boolean(background?.enabled),
        abstract: Boolean(abstract?.enabled),
      },
    });
  }

  return (
    <HydrationBoundary state={dehydrate(client)}>
      <DriverProfileClient />
    </HydrationBoundary>
  );
}
