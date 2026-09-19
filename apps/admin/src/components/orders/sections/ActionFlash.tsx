"use client";

import { cn } from "@porterchain/ui/utils";

/** Inline success/error flash for order actions (replaces window.alert). */
export function ActionFlash({
  error,
  notice,
  className,
}: {
  error?: string | null;
  notice?: string | null;
  className?: string;
}) {
  if (!error && !notice) return null;
  return (
    <div className={cn("space-y-2", className)}>
      {error ? (
        <p className="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      ) : null}
      {notice ? (
        <p className="rounded-xl border border-secondary/20 bg-secondary/5 px-3 py-2 text-sm text-primary">
          {notice}
        </p>
      ) : null}
    </div>
  );
}

export function SectionBlock({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h3 className="mb-3 border-b border-primary/10 pb-2 text-sm font-semibold uppercase tracking-wide text-muted">
        {title}
      </h3>
      {children}
    </div>
  );
}
