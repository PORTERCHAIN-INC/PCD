"use client";

import { useState } from "react";
import Link from "next/link";
import { PackagePlus, Search } from "lucide-react";
import { useApiData } from "@/hooks/useApiData";
import { routeCenter } from "@/lib/route-center";
import { Badge, Button, Input, Spinner } from "@/components/crm/primitives";
import { titleCase } from "@/lib/crmFormat";
import { cn } from "@porterchain/ui/utils";
import {
  RouteEmptyState,
  RouteErrorState,
  RouteSectionCard,
} from "@/components/routes/RouteCenterPrimitives";

const BUCKETS = [
  { key: "website_orders", label: "Website", tone: "blue" as const },
  { key: "merchant_orders", label: "Merchant", tone: "violet" as const },
  { key: "scheduled_orders", label: "Scheduled", tone: "sky" as const },
  { key: "express_orders", label: "Express", tone: "red" as const },
  { key: "returns", label: "Returns", tone: "amber" as const },
  { key: "ready_for_planning", label: "Ready", tone: "green" as const },
] as const;

export default function PlanningQueuePage() {
  const [selected, setSelected] = useState<string[]>([]);
  const [activeBucket, setActiveBucket] =
    useState<(typeof BUCKETS)[number]["key"]>("ready_for_planning");
  const [query, setQuery] = useState("");
  const { data, error } = useApiData((t) => routeCenter.planningQueue(t), [], {
    key: "route-planning-queue",
  });

  if (error) return <RouteErrorState message={error} />;
  if (!data) return <Spinner label="Loading planning queue…" />;

  const toggle = (id: string) =>
    setSelected((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));

  const totalWaiting = BUCKETS.reduce((sum, b) => sum + (data[b.key]?.length ?? 0), 0);
  const bucket = BUCKETS.find((b) => b.key === activeBucket)!;
  const items = (data[activeBucket] ?? []).filter((item) => {
    if (!query.trim()) return true;
    const q = query.toLowerCase();
    const id = String(item.id ?? "");
    const tracking = String(item.tracking_number ?? item.order_number ?? id).toLowerCase();
    const merchant = String(item.merchant ?? "").toLowerCase();
    return tracking.includes(q) || merchant.includes(q) || id.toLowerCase().includes(q);
  });

  return (
    <div className="space-y-6">
      <RouteSectionCard
        title="Planning Queue"
        description={`${totalWaiting} orders across ${BUCKETS.length} buckets — select orders to build a route.`}
        action={
          selected.length > 0 ? (
            <Link href={`/routes/builder?orders=${selected.join(",")}`}>
              <Button className="gap-2">
                <PackagePlus className="h-4 w-4" />
                Build route ({selected.length})
              </Button>
            </Link>
          ) : undefined
        }
      >
        <div className="mb-4 flex flex-wrap gap-2">
          {BUCKETS.map((b) => {
            const count = data[b.key]?.length ?? 0;
            const active = activeBucket === b.key;
            return (
              <button
                key={b.key}
                type="button"
                onClick={() => setActiveBucket(b.key)}
                className={cn(
                  "inline-flex items-center gap-2 rounded-xl border px-3 py-2 text-sm font-medium transition-colors",
                  active
                    ? "border-secondary bg-secondary text-white"
                    : "border-primary/10 bg-white text-primary/70 hover:border-secondary/30"
                )}
              >
                {b.label}
                <Badge
                  tone={active ? "slate" : b.tone}
                  className={active ? "bg-white/20 text-white ring-white/30" : undefined}
                >
                  {count}
                </Badge>
              </button>
            );
          })}
        </div>

        <div className="relative mb-4 max-w-md">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search tracking, merchant, or order ID…"
            className="pl-9"
          />
        </div>

        {items.length === 0 ? (
          <RouteEmptyState
            title={`No orders in ${bucket.label}`}
            hint={
              query
                ? "Try a different search term or bucket."
                : "Orders will appear here when ready for planning."
            }
          />
        ) : (
          <div className="overflow-hidden rounded-xl border border-primary/10">
            <div className="grid grid-cols-[auto_1fr_auto] gap-3 border-b border-primary/10 bg-gray-bg/60 px-4 py-2 text-xs font-semibold uppercase tracking-wide text-muted">
              <span>Select</span>
              <span>Order</span>
              <span>Priority</span>
            </div>
            <div className="divide-y divide-primary/5">
              {items.map((item) => {
                const id = String(item.id ?? "");
                const checked = selected.includes(id);
                return (
                  <label
                    key={`${activeBucket}-${id}`}
                    className={cn(
                      "grid cursor-pointer grid-cols-[auto_1fr_auto] items-center gap-3 px-4 py-3 transition-colors hover:bg-primary/[0.02]",
                      checked && "bg-secondary/[0.04]"
                    )}
                  >
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => toggle(id)}
                      className="h-4 w-4 rounded border-primary/20 text-secondary"
                    />
                    <div className="min-w-0">
                      <p className="font-medium text-primary">
                        {String(item.tracking_number ?? item.order_number ?? id)}
                      </p>
                      <p className="truncate text-xs text-muted">
                        {String(item.merchant ?? "Direct")} ·{" "}
                        {titleCase(String(item.state ?? "unknown"))}
                      </p>
                    </div>
                    {item.high_priority ? (
                      <Badge tone="red">Express</Badge>
                    ) : (
                      <Badge tone="slate">Standard</Badge>
                    )}
                  </label>
                );
              })}
            </div>
          </div>
        )}
      </RouteSectionCard>
    </div>
  );
}
