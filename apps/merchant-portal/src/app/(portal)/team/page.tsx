import { dehydrate, HydrationBoundary, QueryClient } from "@tanstack/react-query";
import TeamClient from "@/components/team/TeamClient";
import { merchantOrgId, merchantServerFetch } from "@/lib/server-api";

export default async function TeamPage() {
  const orgId = await merchantOrgId();
  const client = new QueryClient();
  if (orgId) {
    const [overview, contacts, members, activity, roles, twoFactor] = await Promise.all([
      merchantServerFetch<unknown>("/v1/merchant/team/overview", orgId),
      merchantServerFetch<unknown>("/v1/merchant/contacts", orgId),
      merchantServerFetch<unknown>("/v1/merchant/team", orgId),
      merchantServerFetch<unknown>("/v1/merchant/team/activity", orgId),
      merchantServerFetch<unknown>("/v1/merchant/team/roles", orgId),
      merchantServerFetch<unknown>("/v1/merchant/team/two-factor", orgId),
    ]);
    if (overview && contacts && members && activity && roles && twoFactor) {
      client.setQueryData(["merchant-team", orgId], {
        overview,
        contacts,
        members,
        activity,
        roles,
        twoFactor,
      });
    }
  }

  return (
    <HydrationBoundary state={dehydrate(client)}>
      <TeamClient />
    </HydrationBoundary>
  );
}
