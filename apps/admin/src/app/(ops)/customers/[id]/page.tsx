"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, Mail, Phone, ShieldAlert, Users } from "lucide-react";
import { useApiData } from "@/hooks/useApiData";
import { customersApi } from "@/lib/customers";
import { EntityAlertsPanel } from "@/components/alerts/EntityAlertsPanel";
import { Badge, Button, EmptyState, SectionCard, Spinner } from "@/components/crm/primitives";
import { money, shortDate, titleCase } from "@/lib/crmFormat";

export default function CustomerDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { data, error, loading } = useApiData((t) => customersApi.detail(t, id), [id], {
    key: `customer-${id}`,
  });
  const {
    data: orders,
    error: ordersError,
    loading: ordersLoading,
  } = useApiData((t) => customersApi.orders(t, id), [id], {
    key: `customer-orders-${id}`,
  });

  if (loading && !data) return <Spinner label="Loading customer…" />;
  if (error || !data) {
    return <EmptyState title="Customer not found" hint={error || "Unknown customer"} />;
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <Button variant="outline" onClick={() => router.push("/customers")}>
            <ArrowLeft className="h-4 w-4" /> Back
          </Button>
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-2xl font-bold text-primary">{data.display_name}</h1>
              <Badge tone={data.clerk_linked ? "green" : "slate"}>
                {data.clerk_linked ? "Clerk linked" : "Orphan row"}
              </Badge>
              {data.privacy_status === "deletion_hold" && (
                <Badge tone="amber">
                  <ShieldAlert className="mr-1 inline h-3 w-3" />
                  DSR hold
                </Badge>
              )}
            </div>
            <p className="mt-1 flex flex-wrap items-center gap-3 text-sm text-muted">
              <span className="inline-flex items-center gap-1">
                <Mail className="h-3.5 w-3.5" />
                {data.email}
              </span>
              {data.phone && (
                <span className="inline-flex items-center gap-1">
                  <Phone className="h-3.5 w-3.5" />
                  {data.phone}
                </span>
              )}
              {data.customer_reference && <span>Ref {data.customer_reference}</span>}
              {data.stripe_customer_id && (
                <span className="font-mono text-xs">Stripe {data.stripe_customer_id}</span>
              )}
            </p>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link
            href={`/support?customer_id=${data.id}`}
            className="inline-flex items-center gap-2 rounded-xl border border-primary/15 bg-white px-3.5 py-2 text-sm font-medium text-primary hover:bg-gray-bg"
          >
            <Users className="h-4 w-4" /> Support tickets
          </Link>
          <Link
            href={`/claims?customer_id=${data.id}`}
            className="inline-flex items-center gap-2 rounded-xl border border-primary/15 bg-white px-3.5 py-2 text-sm font-medium text-primary hover:bg-gray-bg"
          >
            Claims
          </Link>
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        <SectionCard title="Lifetime orders">
          <p className="p-5 text-2xl font-semibold text-primary">{data.lifetime_orders}</p>
        </SectionCard>
        <SectionCard title="Lifetime revenue">
          <p className="p-5 text-2xl font-semibold text-primary">
            {money(data.lifetime_revenue_cents)}
          </p>
        </SectionCard>
        <SectionCard title="Open support">
          <p className="p-5 text-2xl font-semibold text-primary">{data.open_support_tickets}</p>
        </SectionCard>
      </div>

      <EntityAlertsPanel
        recipientType="customer"
        recipientId={data.id}
        showDevices
        careHref={`/support?customer_id=${data.id}`}
      />

      <SectionCard title="Identity">
        <dl className="grid gap-3 p-5 sm:grid-cols-2">
          <div>
            <dt className="text-xs uppercase text-muted">Clerk user</dt>
            <dd className="text-sm text-primary">{data.clerk_user_id ?? "—"}</dd>
          </div>
          <div>
            <dt className="text-xs uppercase text-muted">Privacy</dt>
            <dd className="text-sm text-primary">
              {data.privacy_status
                ? `${data.privacy_status}${data.privacy_hold_reference ? ` · ${data.privacy_hold_reference}` : ""}`
                : "—"}
            </dd>
          </div>
          <div>
            <dt className="text-xs uppercase text-muted">Created</dt>
            <dd className="text-sm text-primary">
              {data.created_at ? shortDate(data.created_at) : "—"}
            </dd>
          </div>
        </dl>
      </SectionCard>

      <SectionCard title="Orders">
        {ordersLoading ? (
          <Spinner label="Loading orders…" />
        ) : ordersError ? (
          <p className="p-5 text-sm text-red-600">{ordersError}</p>
        ) : !orders?.length ? (
          <p className="p-5 text-sm text-muted">No orders yet.</p>
        ) : (
          <div className="divide-y divide-primary/5">
            {orders.map((o) => (
              <Link
                key={o.id}
                href={`/orders/${o.id}`}
                className="flex items-center justify-between px-5 py-3 hover:bg-gray-bg/50"
              >
                <div>
                  <p className="text-sm font-medium text-primary">{o.order_number}</p>
                  <p className="text-xs text-muted">
                    {o.tracking_number} · {o.created_at ? shortDate(o.created_at) : "—"}
                  </p>
                </div>
                <div className="text-right">
                  <Badge tone="slate">{titleCase(o.state)}</Badge>
                  <p className="mt-1 text-xs text-muted">{money(o.amount_cents)}</p>
                </div>
              </Link>
            ))}
          </div>
        )}
      </SectionCard>
    </div>
  );
}
