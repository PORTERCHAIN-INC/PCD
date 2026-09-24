"use client";

import { useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  Activity as ActivityIcon,
  ArrowLeft,
  Bell,
  ClipboardList,
  Info,
  LifeBuoy,
  Mail,
  Package,
  Phone,
  Plus,
  Receipt,
  Send,
  Settings as SettingsIcon,
  ShieldAlert,
  Users,
} from "lucide-react";
import { cn } from "@porterchain/ui/utils";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { useAdminProfile } from "@/components/nav/AdminProfileContext";
import { useApiData } from "@/hooks/useApiData";
import {
  customersApi,
  type CreateCustomerBookingDraftResult,
  type CustomerDetail,
} from "@/lib/customers";
import { EntityAlertsPanel } from "@/components/alerts/EntityAlertsPanel";
import { ActivityTimeline } from "@/components/crm/ActivityTimeline";
import { EntityTasks } from "@/components/crm/EntityTasks";
import {
  CustomerAddOrderModal,
  CustomerOrderCreatedBanner,
} from "@/components/customers/CustomerAddOrderModal";
import { Badge, Button, EmptyState, SectionCard, Spinner } from "@/components/crm/primitives";
import { money, shortDate, titleCase } from "@/lib/crmFormat";

/** Mirrors API MODULE_PERMISSIONS["customers"]. */
const CUSTOMERS_WRITE_ROLES = new Set([
  "super_admin",
  "admin",
  "support",
  "support_lead",
  "compliance",
]);

type TabId = "overview" | "orders" | "care" | "billing" | "trust" | "activity" | "tasks";

const TABS: { id: TabId; label: string; icon: React.ComponentType<{ className?: string }> }[] = [
  { id: "overview", label: "Overview", icon: Info },
  { id: "orders", label: "Orders", icon: Package },
  { id: "care", label: "Care", icon: LifeBuoy },
  { id: "billing", label: "Billing", icon: Receipt },
  { id: "trust", label: "Trust", icon: Bell },
  { id: "activity", label: "Activity", icon: ActivityIcon },
  { id: "tasks", label: "Tasks", icon: ClipboardList },
];

export default function CustomerDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { getApiToken } = useAdminAuth();
  const { profile } = useAdminProfile();
  const canWrite = !profile?.role || CUSTOMERS_WRITE_ROLES.has((profile.role || "").toLowerCase());
  const [tab, setTab] = useState<TabId>("overview");
  const [addOrderOpen, setAddOrderOpen] = useState(false);
  const [createdDraft, setCreatedDraft] = useState<CreateCustomerBookingDraftResult | null>(null);
  const [ordersVersion, setOrdersVersion] = useState(0);
  const [detailVersion, setDetailVersion] = useState(0);
  const [inviteBusy, setInviteBusy] = useState(false);
  const [inviteError, setInviteError] = useState<string | null>(null);
  const [inviteOk, setInviteOk] = useState<string | null>(null);
  const { data, error, loading } = useApiData(
    (t) => customersApi.detail(t, id),
    [id, detailVersion],
    {
      key: `customer-${id}-${detailVersion}`,
    }
  );

  async function sendInvite() {
    setInviteBusy(true);
    setInviteError(null);
    setInviteOk(null);
    try {
      const token = await getApiToken();
      const result = await customersApi.invite(token, id);
      setInviteOk(
        result.clerk_action === "found"
          ? "Existing Clerk user linked."
          : "Invite sent to customer portal SignUp."
      );
      setDetailVersion((v) => v + 1);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Invite failed";
      if (msg === "clerk_not_configured") {
        setInviteError("Platform Clerk is not configured — cannot send invite.");
      } else if (msg === "customer_already_clerk_linked") {
        setInviteError("Already Clerk-linked.");
      } else {
        setInviteError(msg);
      }
    } finally {
      setInviteBusy(false);
    }
  }

  if (loading && !data) return <Spinner label="Loading customer…" />;
  if (error || !data) {
    return <EmptyState title="Customer not found" hint={error || "Unknown customer"} />;
  }

  const showInvite = canWrite && !data.clerk_linked && data.privacy_status !== "deletion_hold";

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
            {(inviteError || inviteOk) && (
              <p className={`mt-2 text-sm ${inviteError ? "text-red-600" : "text-green-700"}`}>
                {inviteError || inviteOk}
              </p>
            )}
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          {showInvite && (
            <Button variant="outline" disabled={inviteBusy} onClick={() => void sendInvite()}>
              <Send className="h-4 w-4" /> {inviteBusy ? "Sending…" : "Send invite"}
            </Button>
          )}
          {canWrite && (
            <Button
              onClick={() => {
                setTab("orders");
                setAddOrderOpen(true);
              }}
              disabled={data.privacy_status === "deletion_hold"}
            >
              <Plus className="h-4 w-4" /> Add order
            </Button>
          )}
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
          {data.clerk_linked && (
            <Link
              href={data.settings_users_href || "/settings?section=users&tab=customer"}
              className="inline-flex items-center gap-2 rounded-xl border border-primary/15 bg-white px-3.5 py-2 text-sm font-medium text-primary hover:bg-gray-bg"
            >
              <SettingsIcon className="h-4 w-4" /> Settings → Users
            </Link>
          )}
        </div>
      </div>

      {createdDraft && <CustomerOrderCreatedBanner result={createdDraft} />}

      <div className="grid gap-3 sm:grid-cols-4">
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
        <SectionCard title="Open claims">
          <p className="p-5 text-2xl font-semibold text-primary">{data.open_claims ?? 0}</p>
        </SectionCard>
      </div>

      <div className="flex flex-wrap gap-1 rounded-2xl border border-primary/10 bg-white p-1">
        {TABS.map(({ id: tid, label, icon: Icon }) => (
          <button
            key={tid}
            type="button"
            onClick={() => setTab(tid)}
            className={cn(
              "inline-flex items-center gap-1.5 rounded-xl px-3 py-2 text-sm font-medium transition-colors",
              tab === tid ? "bg-secondary text-white" : "text-primary/70 hover:bg-gray-bg"
            )}
          >
            <Icon className="h-4 w-4" />
            {label}
          </button>
        ))}
      </div>

      {tab === "overview" && <OverviewTab data={data} onGoto={setTab} />}
      {tab === "orders" && (
        <OrdersTab
          id={id}
          version={ordersVersion}
          onAddOrder={() => setAddOrderOpen(true)}
          canAddOrder={canWrite && data.privacy_status !== "deletion_hold"}
        />
      )}
      {tab === "care" && <CareTab id={id} />}
      {tab === "billing" && <BillingTab id={id} stripeCustomerId={data.stripe_customer_id} />}
      {tab === "trust" && (
        <EntityAlertsPanel
          recipientType="customer"
          recipientId={data.id}
          showDevices
          careHref={`/support?customer_id=${data.id}`}
        />
      )}
      {tab === "activity" && <ActivityTimeline entityType="customer" entityId={id} />}
      {tab === "tasks" && <EntityTasks entityType="customer" entityId={id} />}

      <CustomerAddOrderModal
        customerId={id}
        customerEmail={data.email}
        open={addOrderOpen}
        onClose={() => setAddOrderOpen(false)}
        onCreated={(result) => {
          setCreatedDraft(result);
          setOrdersVersion((v) => v + 1);
          setTab("orders");
          if (result.checkout_url) {
            window.open(result.checkout_url, "_blank", "noopener,noreferrer");
          }
        }}
      />
    </div>
  );
}

function OverviewTab({ data, onGoto }: { data: CustomerDetail; onGoto: (t: TabId) => void }) {
  return (
    <div className="space-y-4">
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
            <dt className="text-xs uppercase text-muted">Last order</dt>
            <dd className="text-sm text-primary">
              {data.last_order_at ? shortDate(data.last_order_at) : "—"}
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

      <SectionCard title="Recent orders">
        {!data.recent_orders?.length ? (
          <p className="p-5 text-sm text-muted">No orders yet.</p>
        ) : (
          <div className="divide-y divide-primary/5">
            {data.recent_orders.map((o) => (
              <Link
                key={o.order_id}
                href={`/orders/${o.order_id}`}
                className="flex items-center justify-between px-5 py-3 hover:bg-gray-bg/50"
              >
                <div>
                  <p className="text-sm font-medium text-primary">{o.order_number}</p>
                  <p className="text-xs text-muted">{o.tracking_number}</p>
                </div>
                <div className="text-right">
                  <Badge tone="slate">{titleCase(o.state)}</Badge>
                  <p className="mt-1 text-xs text-muted">{money(o.amount_cents)}</p>
                </div>
              </Link>
            ))}
          </div>
        )}
        <div className="border-t border-primary/5 px-5 py-3">
          <button
            type="button"
            onClick={() => onGoto("orders")}
            className="text-sm font-medium text-secondary hover:underline"
          >
            View all orders →
          </button>
        </div>
      </SectionCard>
    </div>
  );
}

function OrdersTab({
  id,
  version,
  onAddOrder,
  canAddOrder,
}: {
  id: string;
  version: number;
  onAddOrder: () => void;
  canAddOrder: boolean;
}) {
  const {
    data: orders,
    error,
    loading,
  } = useApiData((t) => customersApi.orders(t, id), [id, version], {
    key: `customer-orders-${id}-${version}`,
  });

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button onClick={onAddOrder} disabled={!canAddOrder}>
          <Plus className="h-4 w-4" /> Add order
        </Button>
      </div>
      {loading && !orders ? (
        <Spinner label="Loading orders…" />
      ) : error ? (
        <EmptyState title="Could not load orders" hint={error} />
      ) : !orders?.length ? (
        <EmptyState
          title="No orders yet"
          hint="Create a retail booking draft and send a Stripe payment link."
        />
      ) : (
        <SectionCard title={`Orders (${orders.length})`}>
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
        </SectionCard>
      )}
    </div>
  );
}

function CareTab({ id }: { id: string }) {
  const { data, error, loading } = useApiData((t) => customersApi.care(t, id), [id], {
    key: `customer-care-${id}`,
  });

  if (loading && !data) return <Spinner label="Loading care…" />;
  if (error || !data)
    return <EmptyState title="Could not load care" hint={error || "Unknown error"} />;

  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-2">
        <SectionCard title="Open support">
          <p className="p-5 text-2xl font-semibold text-primary">{data.open_support_tickets}</p>
        </SectionCard>
        <SectionCard title="Open claims">
          <p className="p-5 text-2xl font-semibold text-primary">{data.open_claims}</p>
        </SectionCard>
      </div>

      <SectionCard
        title="Support tickets"
        action={
          <Link
            href={`/support?customer_id=${id}`}
            className="text-sm text-secondary hover:underline"
          >
            Open Support →
          </Link>
        }
      >
        {!data.support_tickets.length ? (
          <p className="p-5 text-sm text-muted">No support tickets.</p>
        ) : (
          <div className="divide-y divide-primary/5">
            {data.support_tickets.map((t) => (
              <Link
                key={t.id}
                href={`/support?customer_id=${id}`}
                className="flex items-center justify-between px-5 py-3 hover:bg-gray-bg/50"
              >
                <div>
                  <p className="text-sm font-medium text-primary">{t.subject}</p>
                  <p className="text-xs text-muted">
                    {t.created_at ? shortDate(t.created_at) : "—"}
                  </p>
                </div>
                <Badge tone="slate">{titleCase(t.status)}</Badge>
              </Link>
            ))}
          </div>
        )}
      </SectionCard>

      <SectionCard
        title="Claims"
        action={
          <Link
            href={`/claims?customer_id=${id}`}
            className="text-sm text-secondary hover:underline"
          >
            Open Claims →
          </Link>
        }
      >
        {!data.claims.length ? (
          <p className="p-5 text-sm text-muted">No claims.</p>
        ) : (
          <div className="divide-y divide-primary/5">
            {data.claims.map((c) => (
              <Link
                key={c.id}
                href={`/claims/${c.id}`}
                className="flex items-center justify-between px-5 py-3 hover:bg-gray-bg/50"
              >
                <div>
                  <p className="text-sm font-medium text-primary">{titleCase(c.claim_type)}</p>
                  <p className="text-xs text-muted">
                    Order {c.order_id.slice(0, 8)}… · {c.created_at ? shortDate(c.created_at) : "—"}
                  </p>
                </div>
                <Badge tone="slate">{titleCase(c.status)}</Badge>
              </Link>
            ))}
          </div>
        )}
      </SectionCard>
    </div>
  );
}

function BillingTab({ id, stripeCustomerId }: { id: string; stripeCustomerId?: string | null }) {
  const {
    data: invoices,
    error: invError,
    loading: invLoading,
  } = useApiData((t) => customersApi.invoices(t, id), [id], {
    key: `customer-invoices-${id}`,
  });
  const {
    data: payments,
    error: payError,
    loading: payLoading,
  } = useApiData((t) => customersApi.payments(t, id), [id], {
    key: `customer-payments-${id}`,
  });

  return (
    <div className="space-y-4">
      <SectionCard title="Stripe">
        <p className="p-5 font-mono text-sm text-primary">{stripeCustomerId || "—"}</p>
      </SectionCard>

      <SectionCard title="Invoices">
        {invLoading && !invoices ? (
          <Spinner label="Loading invoices…" />
        ) : invError ? (
          <p className="p-5 text-sm text-red-600">{invError}</p>
        ) : !invoices?.length ? (
          <p className="p-5 text-sm text-muted">No invoices.</p>
        ) : (
          <div className="divide-y divide-primary/5">
            {invoices.map((inv) => (
              <div key={inv.id} className="flex items-center justify-between px-5 py-3">
                <div>
                  <p className="text-sm font-medium text-primary">{inv.invoice_number}</p>
                  <p className="text-xs text-muted">
                    {inv.created_at ? shortDate(inv.created_at) : "—"}
                    {inv.stripe_receipt_url && (
                      <>
                        {" · "}
                        <a
                          href={inv.stripe_receipt_url}
                          target="_blank"
                          rel="noreferrer"
                          className="text-secondary hover:underline"
                        >
                          Receipt
                        </a>
                      </>
                    )}
                  </p>
                </div>
                <p className="text-sm text-primary">{money(inv.amount_cents)}</p>
              </div>
            ))}
          </div>
        )}
      </SectionCard>

      <SectionCard title="Payments">
        {payLoading && !payments ? (
          <Spinner label="Loading payments…" />
        ) : payError ? (
          <p className="p-5 text-sm text-red-600">{payError}</p>
        ) : !payments?.length ? (
          <p className="p-5 text-sm text-muted">No payments.</p>
        ) : (
          <div className="divide-y divide-primary/5">
            {payments.map((p) => (
              <div key={p.id} className="flex items-center justify-between px-5 py-3">
                <div>
                  <p className="text-sm font-medium text-primary">
                    {p.payment_reference || p.id.slice(0, 8)}
                  </p>
                  <p className="text-xs text-muted">
                    {titleCase(p.status)} · {p.created_at ? shortDate(p.created_at) : "—"}
                  </p>
                </div>
                <p className="text-sm text-primary">{money(p.amount_cents)}</p>
              </div>
            ))}
          </div>
        )}
      </SectionCard>
    </div>
  );
}
