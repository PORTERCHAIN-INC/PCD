"use client";

import { useEffect, useState } from "react";
import { cn } from "@porterchain/ui/utils";
import { useApiData } from "@/hooks/useApiData";
import { ops } from "@/lib/operations";
import { Button, EmptyState, SectionCard } from "@/components/crm/primitives";
import { relativeTime, titleCase } from "@/lib/crmFormat";

const FOLLOW_KEY = "porterchain.ops.followOrderIds";

function readFollowed(): string[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(FOLLOW_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed.filter((x): x is string => typeof x === "string") : [];
  } catch {
    return [];
  }
}

function writeFollowed(ids: string[]) {
  localStorage.setItem(FOLLOW_KEY, JSON.stringify(ids.slice(0, 20)));
}

export function ActivityPanel({
  tick,
  compact,
  followOrderId,
  onOpenOrder,
}: {
  tick: number;
  compact?: boolean;
  followOrderId?: string | null;
  onOpenOrder?: (id: string) => void;
}) {
  const { data } = useApiData((t) => ops.activity(t), [tick], { key: "ops-activity" });
  const [followed, setFollowed] = useState<string[]>(() => readFollowed());
  const [followOnly, setFollowOnly] = useState(false);
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    writeFollowed(followed);
  }, [followed]);

  function toggleFollow(orderId: string) {
    setFollowed((prev) =>
      prev.includes(orderId) ? prev.filter((id) => id !== orderId) : [...prev, orderId]
    );
  }

  const filtered = (data ?? []).filter((e) =>
    followOnly && followed.length ? followed.includes(e.aggregate_id) : true
  );
  const rows = compact ? filtered.slice(0, 8) : filtered;

  if (compact && collapsed) {
    return (
      <button
        type="button"
        onClick={() => setCollapsed(false)}
        className="w-full rounded-xl border border-primary/10 bg-white px-4 py-2 text-left text-xs font-medium text-primary/80 hover:bg-gray-bg/50"
      >
        Show live activity ({filtered.length})
      </button>
    );
  }

  return (
    <SectionCard
      title={compact ? "Live activity feed" : "Live activity"}
      action={
        <div className="flex items-center gap-2">
          {compact && (
            <Button variant="ghost" className="text-xs" onClick={() => setCollapsed(true)}>
              Collapse
            </Button>
          )}
          {!compact && followOrderId && (
            <Button
              variant="outline"
              className="text-xs"
              onClick={() => toggleFollow(followOrderId)}
            >
              {followed.includes(followOrderId) ? "Unfollow open order" : "Follow open order"}
            </Button>
          )}
          {!compact && (
            <Button
              variant={followOnly ? "primary" : "outline"}
              className="text-xs"
              onClick={() => setFollowOnly((v) => !v)}
              disabled={!followed.length}
            >
              Follow mode {followed.length ? `(${followed.length})` : ""}
            </Button>
          )}
        </div>
      }
    >
      <div className={cn("divide-y divide-primary/5", compact && "max-h-64 overflow-y-auto")}>
        {rows.map((e) => (
          <div key={e.id} className="flex items-center justify-between px-5 py-2.5">
            <div className="flex items-center gap-3">
              <span
                className={cn(
                  "h-2 w-2 rounded-full",
                  followed.includes(e.aggregate_id) ? "bg-amber-500" : "bg-secondary"
                )}
              />
              <div>
                <p className="text-sm text-primary">
                  {titleCase(e.event_type.replace(/\./g, " "))}
                </p>
                <p className="text-xs text-muted">
                  {titleCase(e.aggregate_type)} · {titleCase(e.actor_type)}
                  {e.aggregate_type === "order" && onOpenOrder ? (
                    <>
                      {" · "}
                      <button
                        type="button"
                        className="text-secondary hover:underline"
                        onClick={() => onOpenOrder(e.aggregate_id)}
                      >
                        open
                      </button>
                      {" · "}
                      <button
                        type="button"
                        className="text-muted hover:underline"
                        onClick={() => toggleFollow(e.aggregate_id)}
                      >
                        {followed.includes(e.aggregate_id) ? "unfollow" : "follow"}
                      </button>
                    </>
                  ) : null}
                </p>
              </div>
            </div>
            <span className="text-xs text-muted">{relativeTime(e.occurred_at)}</span>
          </div>
        ))}
        {rows.length === 0 && (
          <EmptyState
            title={followOnly ? "No followed-order events" : "No recent activity"}
            hint={followOnly ? "Follow orders from this feed or Order 360." : undefined}
          />
        )}
      </div>
    </SectionCard>
  );
}
