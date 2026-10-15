"use client";

import type { OrderDetail } from "@/lib/orders";
import { Card } from "./shared";

export function DriverTab({
  driver,
  status,
}: {
  driver: Record<string, unknown> | null | undefined;
  status?: string | null;
}) {
  if (!driver) return <Card title="Driver">No driver assigned yet.</Card>;
  return (
    <Card title="Driver">
      <p className="font-medium">{String(driver.name ?? "—")}</p>
      <p className="mt-1 text-muted">
        Status: {status ?? String(driver.is_online ? "online" : "offline")}
      </p>
    </Card>
  );
}
