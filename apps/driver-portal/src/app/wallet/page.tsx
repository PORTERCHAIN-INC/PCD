"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import DriverShell from "@/components/DriverShell";
import { driverApi } from "@/lib/api";
import { formatCents } from "@/lib/utils";

export default function WalletPage() {
  const router = useRouter();
  const [data, setData] = useState<Awaited<ReturnType<typeof driverApi.wallet>> | null>(null);

  useEffect(() => {
    if (!localStorage.getItem("driver_access_token")) router.replace("/login");
    else driverApi.wallet().then(setData);
  }, [router]);

  return (
    <DriverShell walletCents={data?.balance_cents}>
      <h1 className="text-2xl font-bold">Wallet</h1>
      {data && (
        <>
          <p className="mt-2 text-3xl font-bold text-[var(--secondary)]">
            {formatCents(data.balance_cents)}
          </p>
          <h2 className="mt-8 font-semibold">Recent transactions</h2>
          <ul className="mt-3 space-y-2">
            {(data.transactions as { description: string; amount_cents: number }[]).map((t, i) => (
              <li key={i} className="rounded-xl bg-white px-4 py-3 text-sm flex justify-between">
                <span>{t.description || "Transaction"}</span>
                <span className="font-medium">{formatCents(t.amount_cents)}</span>
              </li>
            ))}
          </ul>
        </>
      )}
    </DriverShell>
  );
}
