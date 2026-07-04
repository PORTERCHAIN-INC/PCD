"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import DriverShell from "@/components/DriverShell";
import { driverApi, hasDriverSession } from "@/lib/api";

export default function TrainingPage() {
  const router = useRouter();
  const [modules, setModules] = useState<unknown[]>([]);

  useEffect(() => {
    hasDriverSession().then((ok) => {
      if (!ok) router.replace("/login");
      else driverApi.training().then((r) => setModules(r.modules));
    });
  }, [router]);

  return (
    <DriverShell>
      <h1 className="text-2xl font-bold">Training</h1>
      {modules.length === 0 && <p className="mt-4 text-[var(--muted)]">No training modules assigned</p>}
      <ul className="mt-6 space-y-3">
        {(modules as Record<string, unknown>[]).map((mod, i) => (
          <li key={String(mod.id ?? i)} className="rounded-2xl bg-white p-4">
            <p className="font-medium">{String(mod.title ?? mod.name ?? "Module")}</p>
            <p className="text-sm text-[var(--muted)]">
              {mod.completed ? "Completed" : "Pending"}
            </p>
          </li>
        ))}
      </ul>
    </DriverShell>
  );
}
