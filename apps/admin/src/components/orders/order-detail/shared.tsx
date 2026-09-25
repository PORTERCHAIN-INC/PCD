"use client";

import type { ReactNode } from "react";
import { cn } from "@porterchain/ui/utils";
import { Button } from "@/components/crm/primitives";
import type { OrderDetail } from "@/lib/orders";
import type { Order360Actions } from "./types";

export function Meta({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <p>
      <span className="text-muted">{label}: </span>
      <span className={cn("text-primary", mono && "font-mono")}>{value}</span>
    </p>
  );
}

export function SummaryCard({
  label,
  value,
  tone,
  className,
  icon,
}: {
  label: string;
  value: string;
  tone?: "green" | "amber" | "blue";
  className?: string;
  icon?: React.ReactNode;
}) {
  const toneClass =
    className ??
    (tone === "green"
      ? "bg-green-50 text-green-800"
      : tone === "amber"
        ? "bg-amber-50 text-amber-800"
        : tone === "blue"
          ? "bg-blue-50 text-blue-800"
          : "bg-white text-primary");
  return (
    <div className={cn("rounded-xl border border-primary/10 px-3 py-2", toneClass)}>
      <p className="flex items-center gap-1 text-[10px] font-bold uppercase tracking-wide opacity-70">
        {icon}
        {label}
      </p>
      <p className="mt-0.5 truncate text-sm font-semibold capitalize">{value}</p>
    </div>
  );
}

export function QuickActions({
  detail,
  actions,
}: {
  detail: OrderDetail;
  actions: Order360Actions;
}) {
  const merchant = detail.merchant as Record<string, unknown> | null | undefined;
  const merchantEmail = merchant?.email ? String(merchant.email) : null;
  const merchantPhone = merchant?.phone ? String(merchant.phone) : null;

  const items: Array<{
    label: string;
    onClick?: () => void;
    href?: string;
    primary?: boolean;
    danger?: boolean;
  }> = [
    { label: "Assign driver", onClick: actions.onAssignDriver, primary: true },
    { label: "Reassign driver", onClick: actions.onReassignDriver },
    { label: "Mark exception", onClick: () => actions.onMarkException(), danger: true },
    { label: "Cancel order", onClick: actions.onCancel, danger: true },
    { label: "Duplicate order", onClick: actions.onDuplicate },
    { label: "Rebook", onClick: actions.onRebook },
    { label: "Create return", onClick: actions.onCreateReturn },
    { label: "Generate invoice", onClick: actions.onGenerateInvoice },
    { label: "Resend receipt", onClick: actions.onResendReceipt },
    { label: "Refund", onClick: actions.onRefund },
    { label: "Open claim", onClick: actions.onOpenClaim },
    { label: "Open support ticket", onClick: actions.onOpenSupport },
    { label: "Share tracking", onClick: actions.onShareTracking, primary: true },
    {
      label: "Email customer",
      href: detail.customer_email ? `mailto:${detail.customer_email}` : undefined,
    },
    {
      label: "Call customer",
      href: detail.customer_phone ? `tel:${detail.customer_phone}` : undefined,
    },
    { label: "Email merchant", href: merchantEmail ? `mailto:${merchantEmail}` : undefined },
    { label: "Call merchant", href: merchantPhone ? `tel:${merchantPhone}` : undefined },
    { label: "Print preview", onClick: actions.onPrintLabels },
    { label: "Print pickup list", onClick: actions.onPrintManifest },
    { label: "Download shipment record", onClick: actions.onDownloadRecord },
  ];

  return (
    <div className="flex max-w-full flex-wrap gap-1.5">
      {items.map((item) =>
        item.href ? (
          <a key={item.label} href={item.href}>
            <Button variant="outline" className="px-2 py-1 text-xs">
              {item.label}
            </Button>
          </a>
        ) : (
          <Button
            key={item.label}
            variant={item.danger ? "danger" : item.primary ? "primary" : "outline"}
            className="px-2 py-1 text-xs"
            onClick={item.onClick}
          >
            {item.label}
          </Button>
        )
      )}
    </div>
  );
}

export function SidebarSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-primary/10 bg-white p-3">
      <p className="mb-2 text-xs font-bold uppercase tracking-wide text-muted">{title}</p>
      <div className="space-y-1">{children}</div>
    </div>
  );
}

export function SidebarRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-2 text-xs">
      <span className="text-muted">{label}</span>
      <span className="text-right font-medium text-primary">{value}</span>
    </div>
  );
}

export function Row({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex justify-between gap-4 border-b border-primary/5 py-2 text-sm last:border-0">
      <span className="text-muted">{label}</span>
      <span className={cn("text-right text-primary", mono && "font-mono text-xs break-all")}>
        {value}
      </span>
    </div>
  );
}

export function EntityRows({ data }: { data: Record<string, unknown> }) {
  return (
    <>
      {Object.entries(data).map(([k, val]) => {
        if (k === "recent_orders") return null;
        return (
          <Row
            key={k}
            label={k.replace(/_/g, " ")}
            value={val == null ? "—" : typeof val === "object" ? JSON.stringify(val) : String(val)}
          />
        );
      })}
    </>
  );
}
