"use client";

import Link from "next/link";
import { useState } from "react";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { useApiData } from "@/hooks/useApiData";
import { merchantActionMessage, merchants, type MerchantStandingOrder } from "@/lib/merchants";
import { Badge, Button, SectionCard } from "@/components/crm/primitives";
import { dateTime, titleCase } from "@/lib/crmFormat";

const RULE_LABEL: Record<string, string> = {
  daily: "Every day",
  weekly: "Every week",
  biweekly: "Every two weeks",
  monthly: "Every month",
};

function ruleLabel(rule: string): string {
  return RULE_LABEL[rule] ?? titleCase(rule);
}

export default function MerchantStandingOrdersCard({
  id,
  compact = false,
}: {
  id: string;
  compact?: boolean;
}) {
  const { getApiToken } = useAdminAuth();
  const { data, error, refetch } = useApiData((t) => merchants.standingOrders(t, id), [id], {
    key: `merchant-standing-orders-${id}`,
  });
  const [pausingId, setPausingId] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const rows = data ?? [];
  const failed = rows.filter((row) => Boolean(row.last_error));

  async function pause(standingOrderId: string) {
    if (
      !window.confirm(
        "Pause this standing order? It will stop creating bookings until re-enabled in the portal."
      )
    ) {
      return;
    }
    setPausingId(standingOrderId);
    setActionError(null);
    try {
      const token = await getApiToken();
      await merchants.deactivateStandingOrder(token, id, standingOrderId);
      void refetch();
    } catch (e) {
      setActionError(merchantActionMessage(e, "Could not pause standing order"));
    } finally {
      setPausingId(null);
    }
  }

  if (compact) {
    if (error) return null;
    if (failed.length === 0) return null;
    return (
      <SectionCard title="Standing schedules failed">
        <ul className="divide-y divide-primary/5">
          {failed.map((row) => (
            <FailureRow key={row.id} row={row} />
          ))}
        </ul>
      </SectionCard>
    );
  }

  return (
    <SectionCard title={`Standing orders (${rows.length})`}>
      {error ? <p className="px-5 py-4 text-sm text-red-600">{error}</p> : null}
      {actionError ? <p className="px-5 py-2 text-sm text-red-600">{actionError}</p> : null}
      <div className="divide-y divide-primary/5">
        {rows.map((row) => (
          <div key={row.id} className="space-y-1 px-5 py-3">
            <div className="flex flex-wrap items-center gap-2">
              <p className="text-sm font-medium text-primary">
                {row.template_name || "Saved booking"}
              </p>
              <Badge tone={row.is_active ? "green" : "slate"}>{row.is_active ? "On" : "Off"}</Badge>
              {row.is_active ? (
                <Button
                  variant="outline"
                  disabled={pausingId !== null}
                  onClick={() => void pause(row.id)}
                >
                  {pausingId === row.id ? "Pausing…" : "Pause"}
                </Button>
              ) : null}
            </div>
            <p className="text-xs text-muted">
              {ruleLabel(row.recurrence_rule)} · Next {dateTime(row.next_run_at)}
              {row.last_run_at ? ` · Last ${dateTime(row.last_run_at)}` : " · Not run yet"}
            </p>
            {row.last_order_id ? (
              <Link
                href={`/orders/${row.last_order_id}`}
                className="text-xs text-secondary hover:underline"
              >
                Last order
              </Link>
            ) : null}
            {row.last_error ? (
              <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                {row.last_error}
              </p>
            ) : null}
          </div>
        ))}
        {rows.length === 0 && !error ? (
          <p className="px-5 py-10 text-center text-sm text-muted">
            No standing orders for this company.
          </p>
        ) : null}
      </div>
    </SectionCard>
  );
}

function FailureRow({ row }: { row: MerchantStandingOrder }) {
  return (
    <li className="px-5 py-3">
      <p className="text-sm font-medium text-primary">{row.template_name || "Saved booking"}</p>
      <p className="mt-1 text-sm text-red-700">{row.last_error}</p>
    </li>
  );
}
