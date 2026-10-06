"use client";

import { useQuery } from "@tanstack/react-query";
import { PageSkeleton } from "@porterchain/ui/loading";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { driverApi, hasDriverSession } from "@/lib/api";

export default function PerformanceClient() {
  const router = useRouter();

  useEffect(() => {
    void hasDriverSession().then((ok) => {
      if (!ok) router.replace("/login");
    });
  }, [router]);

  const { data } = useQuery({
    queryKey: ["driver-performance"],
    queryFn: () => driverApi.performance(),
  });

  if (!data) return <PageSkeleton rows={3} />;

  return (
    <>
      <h1 className="text-2xl font-bold">Performance</h1>
      <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {(
          [
            ["score", data.score],
            ["on_time_percent", data.on_time_percent],
            ["completion_percent", data.completion_percent],
            ["deliveries_total", data.deliveries_total],
            ["deliveries_today", data.deliveries_today],
            ["acceptance_rate", data.acceptance_rate],
            ["rating", data.rating],
          ] as const
        ).map(([key, value]) => (
          <div key={key} className="rounded-2xl bg-white p-5">
            <p className="text-sm capitalize text-[var(--muted)]">{key.replace(/_/g, " ")}</p>
            <p className="mt-1 text-xl font-bold">{String(value)}</p>
          </div>
        ))}
      </div>
    </>
  );
}
