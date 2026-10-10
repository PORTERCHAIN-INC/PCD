"use client";

import { useQuery } from "@tanstack/react-query";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import type { AdminBadgeKey } from "@/lib/admin-nav";
import { dispatch } from "@/lib/dispatch";
import { financeOpsApi } from "@/lib/finance-ops";
import { leadsApi } from "@/lib/leads";
import { supportApi } from "@/lib/support";

type Counts = Partial<Record<AdminBadgeKey, number>>;
const safe = async <T>(p: Promise<T>, pick: (v: T) => number): Promise<number> => {
  try {
    return pick(await p);
  } catch {
    return 0; // role can't read it, or the service is down: no badge rather than an error
  }
};

/** "Needs action" counts for nav badges, only for the badge keys the role can see. */
export function useAdminNavBadges(keys: AdminBadgeKey[]): Counts {
  const { getApiToken, isLoaded } = useAdminAuth();
  const want = new Set(keys);
  const { data } = useQuery({
    queryKey: ["admin-nav-badges", [...want].sort().join(",")],
    enabled: isLoaded && want.size > 0,
    refetchInterval: 60_000,
    staleTime: 30_000,
    queryFn: async (): Promise<Counts> => {
      const t = await getApiToken();
      const [exceptions, leads, calls, cash, tickets] = await Promise.all([
        want.has("exceptions") ? safe(dispatch.exceptions(t, 0), (r) => r.total) : 0,
        want.has("leads") ? safe(leadsApi.agentActivity(t), (r) => r.counts.unassigned) : 0,
        want.has("calls") ? safe(leadsApi.today(t), (r) => r.counts.ready) : 0,
        want.has("cash")
          ? safe(
              financeOpsApi.cash(t),
              (r) => (r.overdue_cents > 0 ? r.merchant_count : 0) + r.interac_open_count
            )
          : 0,
        want.has("tickets") ? safe(supportApi.dashboard(t), (r) => r.open_tickets) : 0,
      ]);
      return { exceptions, leads, calls, cash, tickets };
    },
  });
  return data ?? {};
}
