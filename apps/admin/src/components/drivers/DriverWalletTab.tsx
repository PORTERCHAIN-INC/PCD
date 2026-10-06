"use client";

import { useState } from "react";
import { PageSkeleton } from "@porterchain/ui/loading";
import { Wallet } from "lucide-react";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { useApiData } from "@/hooks/useApiData";
import { drivers } from "@/lib/drivers";
import { Badge, Button, SectionCard } from "@/components/crm/primitives";
import { money, shortDate, titleCase } from "@/lib/crmFormat";
import { Metric } from "@/components/drivers/DriverDetailShared";

export function WalletTab({ id }: { id: string }) {
  const { getApiToken } = useAdminAuth();
  const { data, error, refetch } = useApiData((t) => drivers.payouts(t, id), [id], {
    key: `driver-payouts-${id}`,
  });
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  if (!data && !error) return <PageSkeleton rows={3} />;
  const payouts = data?.payouts ?? [];
  const wallet = data?.wallet_balance_cents ?? 0;

  async function createPayout() {
    if (wallet <= 0) {
      setToast("Wallet has no balance to cash out.");
      setTimeout(() => setToast(null), 2500);
      return;
    }
    setBusy(true);
    try {
      const token = await getApiToken();
      await drivers.createPayout(token, id);
      await refetch();
      setToast("Pending payout created from wallet.");
      setTimeout(() => setToast(null), 2500);
    } catch (err) {
      setToast(err instanceof Error ? err.message : "Payout failed");
      setTimeout(() => setToast(null), 3500);
    } finally {
      setBusy(false);
    }
  }

  async function markPaid(payoutId: string) {
    setBusy(true);
    try {
      const token = await getApiToken();
      await drivers.markPayoutPaid(token, id, payoutId);
      await refetch();
    } catch (err) {
      setToast(err instanceof Error ? err.message : "Mark paid failed");
      setTimeout(() => setToast(null), 3500);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-5">
      {error && (
        <p className="rounded-xl border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-700">
          {error}
        </p>
      )}
      <div className="grid gap-3 sm:grid-cols-3">
        <Metric label="Wallet balance" value={money(wallet)} />
        <Metric label="Pending payouts" value={money(data?.pending_cents ?? 0)} />
        <Metric label="Paid out" value={money(data?.paid_cents ?? 0)} />
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <Button onClick={createPayout} disabled={busy || wallet <= 0}>
          <Wallet className="h-4 w-4" /> Create payout from wallet
        </Button>
        {toast && <span className="text-sm text-muted">{toast}</span>}
      </div>
      <SectionCard title="Payout history">
        <div className="divide-y divide-primary/5">
          {payouts.map((p) => (
            <div key={p.id} className="flex items-center justify-between px-5 py-3">
              <div>
                <p className="text-sm font-medium text-primary">
                  {money(p.amount_cents)}{" "}
                  <span className="text-xs uppercase text-muted">{p.currency}</span>
                </p>
                <p className="text-xs text-muted">
                  {p.reference ?? "—"} · {shortDate(p.created_at)}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <Badge tone={p.status === "paid" ? "green" : "amber"}>{titleCase(p.status)}</Badge>
                {p.status === "pending" && (
                  <Button
                    variant="outline"
                    className="px-2 py-1 text-xs"
                    disabled={busy}
                    onClick={() => markPaid(p.id)}
                  >
                    Mark paid
                  </Button>
                )}
              </div>
            </div>
          ))}
          {payouts.length === 0 && (
            <p className="px-5 py-10 text-center text-sm text-muted">
              No payouts yet — earnings stay in wallet until you create a cash-out.
            </p>
          )}
        </div>
      </SectionCard>
    </div>
  );
}
