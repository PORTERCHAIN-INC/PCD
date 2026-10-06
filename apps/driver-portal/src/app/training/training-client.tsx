"use client";

import { useQuery } from "@tanstack/react-query";
import { PageSkeleton } from "@porterchain/ui/loading";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { driverApi, hasDriverSession } from "@/lib/api";

export default function TrainingClient() {
  const router = useRouter();

  useEffect(() => {
    void hasDriverSession().then((ok) => {
      if (!ok) router.replace("/login");
    });
  }, [router]);

  const { data, isLoading } = useQuery({
    queryKey: ["driver-training"],
    queryFn: () => driverApi.training(),
  });

  const modules = data?.modules ?? [];

  if (isLoading && !data) return <PageSkeleton rows={3} />;

  return (
    <>
      <h1 className="text-2xl font-bold">Training</h1>
      {modules.length === 0 && (
        <p className="mt-4 text-[var(--muted)]">No training modules assigned</p>
      )}
      <ul className="mt-6 space-y-3">
        {(modules as Record<string, unknown>[]).map((mod, i) => (
          <li key={String(mod.id ?? i)} className="rounded-2xl bg-white p-4">
            <p className="font-medium">{String(mod.title ?? mod.name ?? "Module")}</p>
            <p className="text-sm text-[var(--muted)]">{mod.completed ? "Completed" : "Pending"}</p>
          </li>
        ))}
      </ul>
    </>
  );
}
