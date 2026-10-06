"use client";

import { useQuery } from "@tanstack/react-query";
import { PageSkeleton } from "@porterchain/ui/loading";
import DriverShell from "@/components/DriverShell";
import { driverApi } from "@/lib/api";
import { formatCents } from "@/lib/utils";

export default function WalletClient() {
  const { data } = useQuery({
    queryKey: ["driver-wallet"],
    queryFn: () => driverApi.wallet(),
  });

  return (
    <DriverShell>
      <h1 className="text-2xl font-bold">Wallet</h1>
      {data ? (
        <>
          <p className="mt-2 text-3xl font-bold text-[var(--secondary)]">
            {formatCents(data.balance_cents)}
          </p>
          <h2 className="mt-8 font-semibold">Recent transactions</h2>
          <ul className="mt-3 space-y-2">
            {(data.transactions as { description: string; amount_cents: number }[]).map((t, i) => (
              <li key={i} className="flex justify-between rounded-xl bg-white px-4 py-3 text-sm">
                <span>{t.description || "Transaction"}</span>
                <span className="font-medium">{formatCents(t.amount_cents)}</span>
              </li>
            ))}
          </ul>
        </>
      ) : (
        <PageSkeleton rows={3} />
      )}
    </DriverShell>
  );
}
