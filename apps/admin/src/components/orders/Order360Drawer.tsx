"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import Link from "next/link";
import { AlertTriangle, Check, Copy, ExternalLink } from "lucide-react";
import { cn } from "@porterchain/ui/utils";
import { useApiData } from "@/hooks/useApiData";
import { ops } from "@/lib/operations";
import { ordersApi } from "@/lib/orders";
import { dateTime, titleCase } from "@/lib/crmFormat";
import { Badge, Button, Drawer, Spinner } from "@/components/crm/primitives";
import { ActionFlash } from "@/components/orders/sections";
import type { ExceptionColumn } from "@/components/orders/ExceptionReasonModal";
import {
  DRAWER_TABS,
  SlaBadge,
  Strip,
  exceptionColumnFromState,
  nextActionFor,
  paymentTone,
  type DrawerTab,
} from "@/components/orders/order360/shared";

const RouteTimeline = dynamic(
  () => import("@/components/orders/order360/shared").then((m) => m.RouteTimeline),
  { loading: () => <Spinner /> }
);
const OrderRouteMap = dynamic(
  () => import("@/components/orders/OrderRouteMap").then((m) => m.OrderRouteMap),
  { loading: () => <Spinner label="Loading map…" /> }
);
const DetailsTab = dynamic(
  () => import("@/components/orders/order360/panels").then((m) => m.DetailsTab),
  { loading: () => <Spinner /> }
);
const TimelineTab = dynamic(
  () => import("@/components/orders/order360/panels").then((m) => m.TimelineTab),
  { loading: () => <Spinner /> }
);
const PodTab = dynamic(() => import("@/components/orders/order360/panels").then((m) => m.PodTab), {
  loading: () => <Spinner />,
});
const MoneyTab = dynamic(
  () => import("@/components/orders/order360/panels").then((m) => m.MoneyTab),
  { loading: () => <Spinner /> }
);
const CareTab = dynamic(
  () => import("@/components/orders/order360/panels").then((m) => m.CareTab),
  { loading: () => <Spinner /> }
);
const OrderAssistPanel = dynamic(
  () => import("@/components/orders/OrderAssistPanel").then((m) => m.OrderAssistPanel),
  { loading: () => <Spinner /> }
);
const AssignDriverModal = dynamic(
  () => import("@/components/orders/AssignDriverModal").then((m) => m.AssignDriverModal),
  { ssr: false }
);
const ExceptionReasonModal = dynamic(
  () => import("@/components/orders/ExceptionReasonModal").then((m) => m.ExceptionReasonModal),
  { ssr: false }
);

export function Order360Drawer({
  orderId,
  onClose,
  onChanged,
}: {
  orderId: string | null;
  onClose: () => void;
  onChanged?: () => void;
}) {
  const {
    data: detail,
    loading,
    error,
    isFetching,
    getApiToken,
    refetch,
  } = useApiData((t) => ordersApi.detail(t, orderId ?? ""), [orderId], {
    key: "order360-drawer",
    enabled: !!orderId,
  });

  const [tab, setTab] = useState<DrawerTab>("overview");
  const [assignOpen, setAssignOpen] = useState(false);
  const [exceptionOpen, setExceptionOpen] = useState(false);
  const [exceptionInitial, setExceptionInitial] = useState<ExceptionColumn | "">("");
  const [actionError, setActionError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  async function copyTracking() {
    if (!detail) return;
    try {
      await navigator.clipboard.writeText(detail.tracking_number);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      setActionError("Could not copy to clipboard");
    }
  }

  const isHigh = detail?.priority?.toLowerCase() === "high";
  const next = detail ? nextActionFor(detail) : null;

  return (
    <>
      <Drawer
        open={!!orderId}
        onClose={onClose}
        width="max-w-2xl"
        title={
          detail ? (
            <span className="flex flex-wrap items-center gap-2">
              <span className="font-mono">{detail.tracking_number}</span>
              <Badge tone="sky">{titleCase(detail.display_state || detail.state)}</Badge>
              <SlaBadge sla={detail.sla_status} />
              {isHigh && <Badge tone="red">High</Badge>}
            </span>
          ) : (
            "Order 360"
          )
        }
        footer={
          detail && (
            <div className="flex w-full flex-wrap items-center gap-2">
              {actionError && (
                <div className="w-full">
                  <ActionFlash error={actionError} />
                </div>
              )}
              <Button
                className="px-3 py-1.5 text-xs"
                onClick={() => setAssignOpen(true)}
                disabled={[
                  "DELIVERED",
                  "POD_COMPLETED",
                  "INVOICED",
                  "CLOSED",
                  "CANCELLED",
                ].includes(detail.state)}
              >
                {detail.driver_name ? "Reassign" : "Assign driver"}
              </Button>
              <Button
                variant="danger"
                className="px-3 py-1.5 text-xs"
                onClick={() => {
                  setExceptionInitial("");
                  setExceptionOpen(true);
                }}
              >
                Mark exception
              </Button>
              <div className="ml-auto flex items-center gap-2">
                <Button
                  variant="outline"
                  className="px-3 py-1.5 text-xs"
                  onClick={() => void copyTracking()}
                >
                  {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
                  {copied ? "Copied" : "Copy tracking"}
                </Button>
                <Link
                  href={`/orders/${detail.order_id}`}
                  className="inline-flex items-center gap-1.5 rounded-xl border border-primary/15 bg-white px-3 py-1.5 text-xs font-medium text-primary hover:bg-gray-bg"
                >
                  Open full page <ExternalLink className="h-3.5 w-3.5" />
                </Link>
              </div>
            </div>
          )
        }
      >
        {loading && !detail ? (
          <Spinner label="Loading order…" />
        ) : error && !detail ? (
          <div className="space-y-3 py-6 text-center">
            <p className="text-sm text-red-600">Could not load order: {error}</p>
            <Button variant="outline" onClick={() => void refetch()} disabled={isFetching}>
              {isFetching ? "Retrying…" : "Retry"}
            </Button>
          </div>
        ) : detail ? (
          <div className="space-y-4">
            {next && (
              <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-secondary/20 bg-secondary/5 px-4 py-3">
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-wide text-secondary">
                    Next best action
                  </p>
                  <p className="text-sm font-semibold text-primary">{next.label}</p>
                  <p className="text-xs text-muted">{next.hint}</p>
                </div>
                <div className="flex flex-wrap gap-2">
                  {next.kind === "assign" && (
                    <Button className="px-3 py-1.5 text-xs" onClick={() => setAssignOpen(true)}>
                      Assign driver
                    </Button>
                  )}
                  {next.kind === "operations" && (
                    <Link href="/operations">
                      <Button variant="outline" className="px-3 py-1.5 text-xs">
                        Open Operations
                      </Button>
                    </Link>
                  )}
                  {next.kind === "money" && (
                    <Button
                      variant="outline"
                      className="px-3 py-1.5 text-xs"
                      onClick={() => setTab("money")}
                    >
                      Open Money
                    </Button>
                  )}
                  {next.kind === "exception" && (
                    <Button
                      variant="danger"
                      className="px-3 py-1.5 text-xs"
                      onClick={() => setExceptionOpen(true)}
                    >
                      Mark exception
                    </Button>
                  )}
                </div>
              </div>
            )}

            <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
              <Strip
                label="Driver"
                value={detail.driver_name ?? "Unassigned"}
                sub={detail.driver_status ? titleCase(detail.driver_status) : detail.vehicle_label}
              />
              <Strip
                label="Promised ETA"
                value={detail.eta ? dateTime(detail.eta) : "—"}
                sub={`SLA ${titleCase(detail.sla_status)}`}
              />
              <Strip
                label="Payment"
                value={
                  <Badge tone={paymentTone(detail.payment_status)}>
                    {titleCase(detail.payment_status ?? "unpaid")}
                  </Badge>
                }
              />
              <Strip
                label="Invoice"
                value={detail.invoice_number ?? "—"}
                sub={titleCase(detail.invoice_status)}
              />
              <Strip
                label="PC ↔ FB"
                value={
                  detail.status_sync?.fleetbase_status
                    ? String(detail.status_sync.fleetbase_status)
                    : "—"
                }
                sub={
                  detail.status_sync?.status_aligned === true
                    ? "Aligned"
                    : detail.status_sync?.status_aligned === false
                      ? "Drift"
                      : String(detail.status_sync?.truth ?? "PC only")
                }
              />
            </div>

            <RouteTimeline detail={detail} />

            {detail.order_id && <OrderRouteMap orderId={detail.order_id} />}

            <div className="rounded-2xl border border-primary/10 bg-white">
              <div className="flex gap-1 overflow-x-auto border-b border-primary/10 px-3 pt-3">
                {DRAWER_TABS.map(({ id, label, icon: Icon }) => (
                  <button
                    key={id}
                    onClick={() => setTab(id)}
                    className={cn(
                      "flex shrink-0 items-center gap-1.5 rounded-t-lg px-3 py-2 text-xs font-medium transition-colors",
                      tab === id ? "bg-gray-bg text-primary" : "text-primary/60 hover:bg-gray-bg/60"
                    )}
                  >
                    <Icon className="h-3.5 w-3.5" />
                    {label}
                  </button>
                ))}
                {isFetching && (
                  <span className="ml-auto self-center text-[11px] text-muted">Refreshing…</span>
                )}
              </div>
              <div className="px-4 py-4">
                {tab === "overview" && <DetailsTab detail={detail} />}
                {tab === "assist" && orderId && (
                  <OrderAssistPanel
                    orderId={orderId}
                    compact
                    onChanged={() => {
                      void refetch();
                      onChanged?.();
                    }}
                    onOpenAssign={() => setAssignOpen(true)}
                    onOpenException={(suggested) => {
                      setExceptionInitial(exceptionColumnFromState(suggested));
                      setExceptionOpen(true);
                    }}
                  />
                )}
                {tab === "journey" && <TimelineTab detail={detail} />}
                {tab === "evidence" && <PodTab detail={detail} />}
                {tab === "money" && <MoneyTab detail={detail} />}
                {tab === "care" && <CareTab detail={detail} />}
              </div>
            </div>

            {detail.incidents.length > 0 && (
              <p className="flex items-center gap-1.5 text-xs text-amber-700">
                <AlertTriangle className="h-3.5 w-3.5" />
                {detail.incidents.length} open incident(s) — see the Care tab.
              </p>
            )}
          </div>
        ) : null}
      </Drawer>

      {assignOpen ? (
        <AssignDriverModal
          open={assignOpen}
          orderId={orderId}
          trackingNumber={detail?.tracking_number}
          currentDriverName={detail?.driver_name}
          onClose={() => setAssignOpen(false)}
          onAssigned={() => {
            void refetch();
            onChanged?.();
          }}
        />
      ) : null}
      {exceptionOpen ? (
        <ExceptionReasonModal
          open={exceptionOpen}
          trackingNumber={detail?.tracking_number}
          initialColumn={exceptionInitial}
          allowColumnChange
          onClose={() => {
            setExceptionOpen(false);
            setExceptionInitial("");
          }}
          onConfirm={async (column, reason) => {
            if (!orderId) return;
            setActionError(null);
            try {
              const token = await getApiToken();
              await ops.moveBoardOrder(token, orderId, column, reason);
              await refetch();
              onChanged?.();
            } catch (e) {
              setActionError(e instanceof Error ? e.message : "Could not mark exception");
              throw e;
            }
          }}
        />
      ) : null}
    </>
  );
}
