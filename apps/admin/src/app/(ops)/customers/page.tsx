"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { Search, Users } from "lucide-react";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { useApiData } from "@/hooks/useApiData";
import { customersApi } from "@/lib/customers";
import { Badge, EmptyState, SectionCard, Spinner } from "@/components/crm/primitives";
import { money, shortDate } from "@/lib/crmFormat";
import { cn } from "@porterchain/ui/utils";

export default function CustomersPage() {
  const { getApiToken, isLoaded, isSignedIn, authReady } = useAdminAuth();
  const [search, setSearch] = useState("");
  const enabled = authReady && isLoaded && (isSignedIn || process.env.NODE_ENV === "development");
  const { data, error, loading } = useApiData(
    (t) => customersApi.list(t, { search: search.trim() || undefined }),
    [search, enabled],
    { key: `customers-${search}`, enabled }
  );

  const rows = useMemo(() => data ?? [], [data]);
  const errMsg = error;

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-primary">Customers</h1>
          <p className="text-sm text-muted">
            Retail demand nodes — self SignUp only; Admin cannot create or invite.
          </p>
        </div>
        <Link
          href="/settings?section=users&tab=customer"
          className={cn(
            "inline-flex items-center justify-center gap-2 rounded-xl border border-primary/15",
            "bg-white px-3.5 py-2 text-sm font-medium text-primary hover:bg-gray-bg"
          )}
        >
          Open in Settings → Users
        </Link>
      </div>

      <div className="relative max-w-md">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
        <input
          type="search"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search email, phone, or reference…"
          className="w-full rounded-xl border border-primary/15 bg-white py-2 pl-9 pr-3 text-sm"
        />
      </div>

      <SectionCard title={`Directory (${rows.length})`}>
        {loading ? (
          <Spinner label="Loading customers…" />
        ) : errMsg ? (
          <EmptyState title="Could not load customers" hint={errMsg} />
        ) : rows.length === 0 ? (
          <EmptyState
            title="No retail customers yet"
            hint="Customers appear after Platform SignUp / website booking."
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-primary/10 bg-gray-bg/40 text-xs uppercase text-muted">
                <tr>
                  <th className="px-4 py-2">Customer</th>
                  <th className="px-4 py-2">Identity</th>
                  <th className="px-4 py-2">Orders</th>
                  <th className="px-4 py-2">Revenue</th>
                  <th className="px-4 py-2">Added</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((c) => (
                  <tr key={c.id} className="border-b border-primary/5 hover:bg-gray-bg/40">
                    <td className="px-4 py-3">
                      <Link href={`/customers/${c.id}`} className="flex items-start gap-2">
                        <span className="mt-0.5 flex h-8 w-8 items-center justify-center rounded-lg bg-primary/5 text-muted">
                          <Users className="h-4 w-4" />
                        </span>
                        <div>
                          <p className="font-medium text-primary hover:underline">
                            {c.display_name || c.email}
                          </p>
                          <p className="text-xs text-muted">{c.email}</p>
                        </div>
                      </Link>
                    </td>
                    <td className="px-4 py-3">
                      <Badge tone={c.clerk_linked ? "green" : "slate"}>
                        {c.clerk_linked ? "Clerk linked" : "Orphan"}
                      </Badge>
                      {c.privacy_status === "deletion_hold" && <Badge tone="amber">DSR hold</Badge>}
                    </td>
                    <td className="px-4 py-3">{c.lifetime_orders}</td>
                    <td className="px-4 py-3">{money(c.lifetime_revenue_cents)}</td>
                    <td className="px-4 py-3 text-xs text-muted">
                      {c.created_at ? shortDate(c.created_at) : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </SectionCard>
    </div>
  );
}
