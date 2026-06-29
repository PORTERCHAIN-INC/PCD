"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import DriverShell from "@/components/DriverShell";
import { driverApi } from "@/lib/api";
import { formatCents } from "@/lib/utils";

export default function DashboardPage() {
  const router = useRouter();
  const [data, setData] = useState<Awaited<ReturnType<typeof driverApi.dashboard>> | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!localStorage.getItem("driver_access_token")) {
      router.replace("/login");
      return;
    }
    driverApi.dashboard().then(setData).catch((e) => setError(String(e.message)));
  }, [router]);

  const toggleOnline = async () => {
    if (!data) return;
    await driverApi.setOnline(!data.is_online);
    setData({ ...data, is_online: !data.is_online });
  };

  if (error) return <p className="text-red-600">{error}</p>;
  if (!data) return <p>Loading…</p>;

  return (
    <DriverShell walletCents={data.wallet_balance_cents}>
      <h1 className="text-2xl font-bold">Driver Dashboard</h1>
      <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[
          { label: "Today's Earnings", value: formatCents(data.todays_earnings_cents) },
          { label: "Today's Stops", value: `${data.todays_stops_completed}/${data.todays_stops_total}` },
          { label: "Wallet", value: formatCents(data.wallet_balance_cents) },
          { label: "Performance", value: `${data.performance_score}%` },
        ].map((card) => (
          <div key={card.label} className="rounded-2xl bg-white p-5 shadow-sm">
            <p className="text-sm text-[var(--muted)]">{card.label}</p>
            <p className="mt-1 text-2xl font-bold">{card.value}</p>
          </div>
        ))}
      </div>
      <div className="mt-6 flex flex-wrap gap-3">
        <button
          type="button"
          onClick={toggleOnline}
          className={`rounded-xl px-5 py-2.5 text-sm font-semibold text-white ${data.is_online ? "bg-gray-600" : "bg-green-600"}`}
        >
          {data.is_online ? "Go Offline" : "Go Online"}
        </button>
        <span className="rounded-xl bg-white px-4 py-2.5 text-sm">
          Rating: {data.rating ?? "—"} · Bonuses: {data.bonuses_available}
        </span>
      </div>
    </DriverShell>
  );
}
