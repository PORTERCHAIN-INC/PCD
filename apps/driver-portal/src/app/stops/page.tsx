"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import DriverShell from "@/components/DriverShell";
import { driverApi } from "@/lib/api";

export default function StopsPage() {
  const router = useRouter();
  const [route, setRoute] = useState<Awaited<ReturnType<typeof driverApi.route>>>(null);

  useEffect(() => {
    if (!localStorage.getItem("driver_access_token")) router.replace("/login");
    else driverApi.route().then(setRoute);
  }, [router]);

  return (
    <DriverShell>
      <h1 className="text-2xl font-bold">Today&apos;s Stops</h1>
      {!route && <p className="mt-4 text-[var(--muted)]">No assigned route</p>}
      {route && (
        <ul className="mt-6 space-y-3">
          {(route.stops as { stop_id: string; stop_type: string; address: { formatted?: string }; status: string }[]).map((s) => (
            <li key={s.stop_id} className="rounded-2xl bg-white p-4">
              <p className="text-xs uppercase text-[var(--muted)]">{s.stop_type}</p>
              <p className="font-medium">{s.address?.formatted || "Address"}</p>
              <p className="text-sm text-[var(--muted)]">{s.status}</p>
            </li>
          ))}
        </ul>
      )}
    </DriverShell>
  );
}
