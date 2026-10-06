"use client";

import Link from "next/link";
import { useDeferredValue, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Link2, Search, ShieldAlert, TrendingUp, UserPlus, UserX, Users } from "lucide-react";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { useAdminProfile } from "@/components/nav/AdminProfileContext";
import { useApiData } from "@/hooks/useApiData";
import { customersApi } from "@/lib/customers";
import { FilterChip } from "@/components/crm/filters";
import { Badge, Button, EmptyState, SectionCard } from "@/components/crm/primitives";
import { money, shortDate } from "@/lib/crmFormat";
import { cn } from "@porterchain/ui/utils";
import { TableSkeleton } from "@porterchain/ui/loading";
import AdminPage from "@/components/layout/AdminPage";
import dynamic from "next/dynamic";

const CustomerCreateModal = dynamic(
  () => import("@/components/customers/CustomerCreateModal").then((m) => m.CustomerCreateModal),
  { ssr: false }
);

/** Mirrors API MODULE_PERMISSIONS["customers"]. */
const CUSTOMERS_WRITE_ROLES = new Set([
  "super_admin",
  "admin",
  "support",
  "support_lead",
  "compliance",
]);

type IdentityFilter = "" | "linked" | "orphan" | "dsr";

export default function CustomersPage() {
  const router = useRouter();
  const { isLoaded, isSignedIn, authReady } = useAdminAuth();
  const { profile } = useAdminProfile();
  const canWrite = !profile?.role || CUSTOMERS_WRITE_ROLES.has((profile.role || "").toLowerCase());
  const [search, setSearch] = useState("");
  const deferredSearch = useDeferredValue(search);
  const [identity, setIdentity] = useState<IdentityFilter>("");
  const [createOpen, setCreateOpen] = useState(false);
  const [version, setVersion] = useState(0);
  const enabled = authReady && isLoaded && (isSignedIn || process.env.NODE_ENV === "development");

  const listParams = useMemo(() => {
    const params: Record<string, string | undefined> = {
      search: deferredSearch.trim() || undefined,
    };
    if (identity === "linked") params.clerk_linked = "true";
    if (identity === "orphan") params.clerk_linked = "false";
    if (identity === "dsr") params.privacy_status = "deletion_hold";
    return params;
  }, [deferredSearch, identity]);

  const { data: stats } = useApiData((t) => customersApi.stats(t), [version], {
    key: `customers-stats-${version}`,
    enabled,
  });
  const { data, error, loading } = useApiData((t) => customersApi.list(t, listParams), [version], {
    key: `customers-${JSON.stringify(listParams)}-${version}`,
    enabled,
  });

  const rows = useMemo(() => data ?? [], [data]);

  return (
    <AdminPage>
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-primary">Customers</h1>
          <p className="text-sm text-muted">
            Retail demand nodes — create for phone-book, or they arrive via website SignUp.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {canWrite && (
            <Button onClick={() => setCreateOpen(true)}>
              <UserPlus className="h-4 w-4" /> Add customer
            </Button>
          )}
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
      </div>

      {stats && (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          <StatTile icon={Users} label="Total customers" value={stats.total.toLocaleString()} />
          <StatTile
            icon={Link2}
            label="Clerk linked"
            value={String(stats.clerk_linked)}
            accent="text-green-600"
          />
          <StatTile
            icon={UserX}
            label="Orphan rows"
            value={String(stats.orphan)}
            accent="text-slate-600"
          />
          <StatTile
            icon={ShieldAlert}
            label="DSR hold"
            value={String(stats.dsr_hold)}
            accent="text-amber-600"
          />
          <StatTile
            icon={TrendingUp}
            label="Revenue (30d)"
            value={money(stats.revenue_30d_cents)}
            accent="text-secondary"
          />
        </div>
      )}

      <div className="flex flex-wrap items-center gap-2">
        <div className="relative min-w-[220px] flex-1 max-w-md">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
          <input
            type="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search email, phone, or reference…"
            className="w-full rounded-xl border border-primary/15 bg-white py-2 pl-9 pr-3 text-sm"
          />
        </div>
        <FacetButton active={identity === ""} onClick={() => setIdentity("")}>
          All
        </FacetButton>
        <FacetButton active={identity === "linked"} onClick={() => setIdentity("linked")}>
          Clerk linked
        </FacetButton>
        <FacetButton active={identity === "orphan"} onClick={() => setIdentity("orphan")}>
          Orphan
        </FacetButton>
        <FacetButton active={identity === "dsr"} onClick={() => setIdentity("dsr")}>
          DSR hold
        </FacetButton>
      </div>

      {identity && (
        <div className="flex flex-wrap gap-2">
          <FilterChip
            label={
              identity === "linked"
                ? "Identity: Clerk linked"
                : identity === "orphan"
                  ? "Identity: Orphan"
                  : "Privacy: DSR hold"
            }
            onRemove={() => setIdentity("")}
          />
        </div>
      )}

      <SectionCard title={`Directory (${rows.length})`}>
        {loading && rows.length === 0 ? (
          <TableSkeleton rows={8} />
        ) : error ? (
          <EmptyState title="Could not load customers" hint={error} />
        ) : rows.length === 0 ? (
          <EmptyState
            title="No retail customers match"
            hint="Add a customer for phone-book, or they appear after website SignUp / booking."
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-primary/10 bg-gray-bg/40 text-xs uppercase text-muted">
                <tr>
                  <th className="px-4 py-2">Customer</th>
                  <th className="px-4 py-2">Identity</th>
                  <th className="px-4 py-2">Privacy</th>
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
                    </td>
                    <td className="px-4 py-3">
                      {c.privacy_status === "deletion_hold" ? (
                        <Badge tone="amber">DSR hold</Badge>
                      ) : (
                        <span className="text-xs text-muted">—</span>
                      )}
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

      <CustomerCreateModal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        onCreated={(result) => {
          setCreateOpen(false);
          setVersion((v) => v + 1);
          router.push(`/customers/${result.id}`);
        }}
      />
    </AdminPage>
  );
}

function FacetButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "rounded-xl border px-3 py-2 text-sm font-medium transition-colors",
        active
          ? "border-secondary/40 bg-secondary/5 text-secondary"
          : "border-primary/15 bg-white text-primary/80 hover:bg-gray-bg"
      )}
    >
      {children}
    </button>
  );
}

function StatTile({
  icon: Icon,
  label,
  value,
  accent = "text-secondary",
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string;
  accent?: string;
}) {
  return (
    <div className="rounded-2xl border border-primary/10 bg-white p-4">
      <div className="flex items-center justify-between">
        <p className="text-xs font-medium text-muted">{label}</p>
        <Icon className={`h-4 w-4 ${accent}`} />
      </div>
      <p className="mt-2 text-2xl font-bold text-primary">{value}</p>
    </div>
  );
}
