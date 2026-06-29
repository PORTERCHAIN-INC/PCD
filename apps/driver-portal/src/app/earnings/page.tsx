"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import DriverShell from "@/components/DriverShell";
import { driverApi } from "@/lib/api";
import { formatCents } from "@/lib/utils";

export default function EarningsPage() {
  const router = useRouter();
  const [data, setData] = useState<{ today_cents: number; week_cents: number } | null>(null);

  useEffect(() => {
    if (!localStorage.getItem("driver_access_token")) router.replace("/login");
    else driverApi.earnings().then(setData);
  }, [router]);

  return (
    <DriverShell>
      <h1 className="text-2xl font-bold">Earnings</h1>
      {data && (
        <div className="mt-6 grid gap-4 sm:grid-cols-2">
          <div className="rounded-2xl bg-white p-5">
            <p className="text-sm text-[var(--muted)]">Today</p>
            <p className="text-2xl font-bold">{formatCents(data.today_cents)}</p>
          </div>
          <div className="rounded-2xl bg-white p-5">
            <p className="text-sm text-[var(--muted)]">This week</p>
            <p className="text-2xl font-bold">{formatCents(data.week_cents)}</p>
          </div>
        </div>
      )}
    </DriverShell>
  );
}
