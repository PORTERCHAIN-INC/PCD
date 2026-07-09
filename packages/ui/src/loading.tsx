"use client";

import { cn } from "./utils";

function Shimmer({ className }: { className?: string }) {
  return <div className={cn("animate-pulse rounded-xl bg-primary/5", className)} />;
}

export function Spinner({ label = "Loading…", className }: { label?: string; className?: string }) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-3 px-6 py-16 text-sm text-muted",
        className
      )}
      role="status"
      aria-live="polite"
    >
      <span className="h-5 w-5 animate-spin rounded-full border-2 border-secondary/30 border-t-secondary" />
      {label}
    </div>
  );
}

export function PageSkeleton({ rows = 3 }: { rows?: number }) {
  return (
    <div className="space-y-4" aria-hidden>
      <Shimmer className="h-9 w-56" />
      <Shimmer className="h-4 w-80 max-w-full" />
      <div className="space-y-3 pt-2">
        {Array.from({ length: rows }).map((_, i) => (
          <Shimmer key={i} className="h-24 w-full" />
        ))}
      </div>
    </div>
  );
}

export function StatCardsSkeleton({ count = 4 }: { count?: number }) {
  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4" aria-hidden>
      {Array.from({ length: count }).map((_, i) => (
        <Shimmer key={i} className="h-28 w-full" />
      ))}
    </div>
  );
}

export function TableSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div className="overflow-hidden rounded-2xl border border-primary/10 bg-white" aria-hidden>
      <Shimmer className="h-11 w-full rounded-none" />
      {Array.from({ length: rows }).map((_, i) => (
        <Shimmer key={i} className="mx-3 my-2 h-10 w-[calc(100%-1.5rem)]" />
      ))}
    </div>
  );
}

export function CardListSkeleton({ count = 4 }: { count?: number }) {
  return (
    <div className="space-y-3" aria-hidden>
      {Array.from({ length: count }).map((_, i) => (
        <Shimmer key={i} className="h-32 w-full" />
      ))}
    </div>
  );
}
